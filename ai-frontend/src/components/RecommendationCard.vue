<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { createRecommendation, decideRecommendation } from '../api/medical'
import { usePatient } from '../composables/usePatient'
import { useWorkflow } from '../composables/useWorkflow'
import { useAssistantContext } from '../composables/useAssistantContext'

const { patient } = usePatient()
const { workflow, canRecommend, applyRecommendation, switchStep } = useWorkflow()
const { askAbout } = useAssistantContext()

const strategyVersion = ref('STRAT-V1')
const creating = ref(false)
const createError = ref('')
const recommendation = ref(null) // RecommendationData

// ── 手动候选（MVP：候选由医师侧指定，正式引擎接入后自动生成） ──
const manualCandidates = reactive([{ medication_id: '', reasons: '', sort_order: 1 }])

function addCandidate() {
  manualCandidates.push({ medication_id: '', reasons: '', sort_order: manualCandidates.length + 1 })
}
function removeCandidate(index) {
  if (manualCandidates.length > 1) manualCandidates.splice(index, 1)
}

async function launch() {
  if (!canRecommend.value) {
    createError.value = '请先完成第①步的病情确认，取得临床评估后再发起推荐。'
    return
  }
  const candidates = manualCandidates
    .filter((item) => String(item.medication_id).trim())
    .map((item, index) => ({
      medication_id: Number(item.medication_id),
      sort_order: index + 1,
      reasons: item.reasons ? [item.reasons] : undefined,
    }))

  creating.value = true
  createError.value = ''
  try {
    const data = await createRecommendation({
      patient_id: patient.context.patient_id,
      encounter_id: patient.context.encounter_id || undefined,
      clinical_assessment_id: workflow.assessmentNo,
      strategy_version: strategyVersion.value,
      candidates: candidates.length ? candidates : undefined,
    })
    recommendation.value = data
    applyRecommendation(data)
  } catch (error) {
    createError.value = error.message
  } finally {
    creating.value = false
  }
}

// ── 医师决定 ──
const decisionType = ref('accepted')
const decisionReason = ref('')
const deciding = ref(false)
const decisionError = ref('')
const decisionResult = ref(null)

const decided = computed(() => recommendation.value?.status === 'decided' || Boolean(decisionResult.value))
const selectableCandidates = computed(
  () => (recommendation.value?.candidates ?? []).filter((item) => item.candidate_status === 'candidate'),
)

const selections = reactive(new Map())

function toggleSelection(candidateId) {
  if (selections.has(candidateId)) selections.delete(candidateId)
  else selections.set(candidateId, { selected: true, action: 'add', reason: '' })
}

watch(() => patient.context?.patient_id, () => {
  recommendation.value = null
  decisionResult.value = null
  decisionError.value = ''
  createError.value = ''
  selections.clear()
})

async function submitDecision() {
  if (!recommendation.value) return
  const chosen = [...selections.keys()]
  if (!chosen.length) {
    decisionError.value = '请至少勾选一个候选进行决定。'
    return
  }
  deciding.value = true
  decisionError.value = ''
  try {
    const result = await decideRecommendation(recommendation.value.recommendation_id, {
      decision_type: decisionType.value,
      reason: decisionReason.value.trim() || undefined,
      items: chosen.map((candidateId) => ({
        candidate_id: candidateId,
        selected: true,
        action: selections.get(candidateId).action,
        reason: selections.get(candidateId).reason.trim() || undefined,
      })),
    })
    decisionResult.value = result
    recommendation.value.status = 'decided'
    workflow.recommendationStatus = 'decided'
    // 决定完成，引导进入第③步开方
    if (decisionType.value !== 'rejected') switchStep('prescription')
  } catch (error) {
    decisionError.value = error.message
  } finally {
    deciding.value = false
  }
}

function severityOf(riskSummary) {
  return riskSummary?.severity ? `status-${riskSummary.severity}` : 'status-muted'
}
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">② 候选用药推荐</h2>
      <p class="panel-subtitle">
        基于已确认的临床评估 · 候选/排除与依据均以业务后端为准
        <span v-if="workflow.recommendationNo" class="status-badge" :class="decided ? 'status-success' : 'status-warning'" style="margin-left:8px">
          {{ workflow.recommendationNo }}
        </span>
      </p>
    </header>

    <div class="panel-body">
      <!-- 发起 -->
      <div class="panel-section">
        <h4>发起推荐任务</h4>
        <div class="form-grid">
          <label class="field-label">临床评估 ID</label>
          <input :value="workflow.assessmentNo || '— 尚未完成病情确认 —'" type="text" class="app-input" disabled />
          <label class="field-label">策略版本</label>
          <input v-model="strategyVersion" type="text" class="app-input" />

          <label class="field-label">手动候选用药（medication 内部 ID，可选）</label>
          <div class="candidate-editor">
            <div v-for="(item, index) in manualCandidates" :key="index" class="candidate-line">
              <input v-model="item.medication_id" type="text" class="app-input id-field" placeholder="如 3001" />
              <input v-model="item.reasons" type="text" class="app-input" placeholder="进入候选的原因(可选)" />
              <button type="button" class="app-button danger-ghost" @click="removeCandidate(index)">✕</button>
            </div>
            <button type="button" class="app-button" @click="addCandidate">+ 添加候选</button>
          </div>
        </div>
        <div class="action-row">
          <button type="button" class="app-button primary" :disabled="creating || !canRecommend || decided" @click="launch">
            {{ creating ? '创建中…' : (decided ? '已有决定' : '发起推荐') }}
          </button>
          <span v-if="!canRecommend && !decided" class="status-badge status-warning">需先完成①</span>
          <span v-if="recommendation" class="status-badge" :class="decided ? 'status-success' : 'status-info'">
            状态：{{ recommendation.status }}
          </span>
        </div>
        <p v-if="createError" class="error-line">{{ createError }}</p>
      </div>

      <!-- 候选列表 -->
      <template v-if="recommendation">
        <article
          v-for="candidate in recommendation.candidates"
          :key="candidate.candidate_id"
          class="panel-section candidate-card"
          :class="{ excluded: candidate.candidate_status === 'excluded', selected: selections.has(candidate.candidate_id) }"
        >
          <div class="card-head">
            <span class="status-badge" :class="candidate.candidate_status === 'excluded' ? 'status-high' : 'status-success'">
              {{ candidate.candidate_status === 'excluded' ? '已排除' : `候选 #${candidate.sort_order ?? '—'}` }}
            </span>
            <strong class="med-name">{{ candidate.medication?.generic_name }}</strong>
            <small class="med-spec">{{ candidate.medication?.specification }} · {{ candidate.medication?.dosage_form }}</small>
          </div>

          <div v-if="candidate.reasons" class="evidence-block">
            <em>入选原因</em>
            <pre>{{ JSON.stringify(candidate.reasons, null, 2) }}</pre>
          </div>
          <div v-if="candidate.risk_summary" class="evidence-block">
            <em><span class="status-badge" :class="severityOf(candidate.risk_summary)">风险摘要</span></em>
            <pre>{{ JSON.stringify(candidate.risk_summary, null, 2) }}</pre>
          </div>
          <div v-if="candidate.monitoring" class="evidence-block">
            <em>监测建议</em>
            <pre>{{ JSON.stringify(candidate.monitoring, null, 2) }}</pre>
          </div>
          <p v-if="candidate.exclusion_reason" class="muted-line">排除原因：{{ candidate.exclusion_reason }}（规则 {{ candidate.exclusion_rule_code }}）</p>

          <div class="action-row" style="margin-top:8px">
            <label v-if="candidate.candidate_status === 'candidate' && !decided" class="choice-item">
              <input type="checkbox" :checked="selections.has(candidate.candidate_id)" @change="toggleSelection(candidate.candidate_id)" />
              <span>采纳该候选</span>
            </label>
            <select v-if="selections.has(candidate.candidate_id)" v-model="selections.get(candidate.candidate_id).action" class="app-select" style="width:auto">
              <option value="add">add 加入草稿</option>
              <option value="replace">replace 替换现有</option>
              <option value="keep">keep 维持现状</option>
            </select>
            <button type="button" class="app-button" @click="askAbout({ type: 'recommendation', id: String(candidate.candidate_id), title: candidate.medication?.generic_name, attributes: { medication_id: candidate.medication?.id, risk_summary: candidate.risk_summary } })">
              问助手
            </button>
          </div>
        </article>

        <!-- 决定 -->
        <div v-if="!decided && selectableCandidates.length" class="panel-section decide-section">
          <h4>医师决定</h4>
          <div class="row-gap">
            <select v-model="decisionType" class="app-select" style="width:auto">
              <option value="accepted">全部采纳</option>
              <option value="partially_accepted">部分采纳</option>
              <option value="rejected">全部不采纳</option>
            </select>
          </div>
          <textarea v-model="decisionReason" class="app-textarea compact" rows="2" placeholder="决定理由（可选）"></textarea>
          <div class="action-row">
            <button type="button" class="app-button primary" :disabled="deciding" @click="submitDecision">
              {{ deciding ? '提交中…' : '提交决定' }}
            </button>
          </div>
        </div>
        <div v-else-if="decided" class="success-line">
          ✓ 推荐决定已完成{{ decisionResult ? `：${decisionResult.decision_type} · ${decisionResult.items.length} 个候选` : '' }}。采纳结果可在第③步创建处方草稿。
        </div>
        <p v-if="decisionError" class="error-line">{{ decisionError }}</p>
      </template>

      <div v-else class="empty-state">
        <span class="empty-icon">💡</span>
        <p>完成病情确认后在此发起候选用药推荐。<br />正式推荐引擎接入后，候选将自动生成并附排除原因。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.form-grid {
  display: flex;
  flex-direction: column;
}
.field-label {
  margin: 10px 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.form-grid > .field-label:first-child {
  margin-top: 0;
}
.candidate-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.candidate-line {
  display: flex;
  gap: 6px;
}
.id-field {
  width: 90px;
  flex-shrink: 0;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.danger-ghost {
  border-color: rgba(251, 113, 133, 0.3);
  color: var(--color-danger);
  min-width: 36px;
}
.candidate-card.selected {
  border-color: rgba(45, 212, 191, 0.35);
}
.candidate-card.excluded {
  opacity: 0.75;
}
.card-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.med-name {
  font-size: 15px;
}
.med-spec {
  color: var(--color-text-muted);
  font-size: 11px;
}
.evidence-block {
  margin-top: 8px;
}
.evidence-block em {
  display: block;
  font-style: normal;
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
.evidence-block pre {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text-primary);
  max-height: 140px;
  overflow-y: auto;
}
.decide-section {
  background: var(--color-accent-soft-bg);
  border-color: rgba(45, 212, 191, 0.25);
}
.choice-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
}
.row-gap {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}
.compact {
  min-height: 52px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 30px 20px;
  text-align: center;
}
.empty-icon {
  font-size: 34px;
  opacity: 0.5;
}
.empty-state p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.7;
}
</style>
