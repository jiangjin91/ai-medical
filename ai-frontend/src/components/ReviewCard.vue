<script setup>
import { computed, ref } from 'vue'
import {
  createReviewTask,
  getReviewTask,
  executeReviewTask,
  decideReviewTask,
  feedbackFinding,
  createIntervention,
  respondIntervention,
} from '../api/medical'
import { useIdentity } from '../composables/useIdentity'
import { useWorkflow } from '../composables/useWorkflow'
import { useAssistantContext } from '../composables/useAssistantContext'

const { identity } = useIdentity()
const { workflow, applyReviewTask } = useWorkflow()
const { askAbout } = useAssistantContext()

const taskIdInput = ref('')
const loading = ref(false)
const loadError = ref('')
const notice = ref('')
const task = ref(null) // ReviewTaskData

const isPhysician = computed(() => ['physician', 'system_admin'].includes(identity.actorRole))
const isPharmacist = computed(() => ['pharmacist', 'review_pharmacist', 'system_admin'].includes(identity.actorRole))
const isExecutor = computed(() => ['service', 'system_admin'].includes(identity.actorRole))

const ACTION_LABEL = { display: '提示', confirm: '需确认', block: '阻断' }
const SEVERITY_ICON = { critical: '⛔', high: '🔴', warning: '🟠', info: '🔵' }

function severityClass(severity) {
  const normalized = (severity ?? '').toLowerCase()
  if (normalized === 'critical') return 'status-critical'
  if (normalized === 'high') return 'status-high'
  if (normalized === 'warning') return 'status-warning'
  return 'status-info'
}

async function refresh(no) {
  const target = no ?? workflow.reviewTaskNo ?? taskIdInput.value.trim()
  if (!target) return
  loading.value = true
  loadError.value = ''
  try {
    task.value = await getReviewTask(target)
    applyReviewTask(task.value)
    taskIdInput.value = task.value.review_task_id
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

async function createTaskForCurrentPrescription() {
  const prescriptionId = workflow.prescriptionNo
  if (!prescriptionId) {
    loadError.value = '请先在第③步创建并提交处方。'
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const data = await createReviewTask({ prescription_id: prescriptionId })
    task.value = data
    applyReviewTask(data)
    taskIdInput.value = data.review_task_id
    notice.value = `审核任务 ${data.review_task_id} 已就绪。`
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

async function executeRules() {
  if (!task.value) return
  loading.value = true
  loadError.value = ''
  try {
    task.value = await executeReviewTask(task.value.review_task_id)
    applyReviewTask(task.value)
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

// ── 药师决定 ──
const decisionType = ref('approved')
const decisionReason = ref('')
const signatureRef = ref('')
const deciding = ref(false)

async function decide() {
  deciding.value = true
  loadError.value = ''
  try {
    await decideReviewTask(task.value.review_task_id, {
      decision_type: decisionType.value,
      decision_reason: decisionReason.value.trim() || undefined,
      signature_reference: signatureRef.value.trim() || undefined,
    })
    await refresh()
    decisionReason.value = ''
  } catch (error) {
    loadError.value = error.message
  } finally {
    deciding.value = false
  }
}

// ── 风险项反馈（医师） ──
const feedbackDrafts = ref({}) // finding_key -> { action, comment }
function draftOf(findingKey) {
  if (!feedbackDrafts.value[findingKey]) feedbackDrafts.value[findingKey] = { action: 'acknowledged', comment: '' }
  return feedbackDrafts.value[findingKey]
}
async function sendFeedback(finding) {
  const draft = draftOf(`${finding.finding_id}|${finding.rule_code}`)
  try {
    // finding_id 是任务内业务号；跨任务出现同名业务号时后端返回 FINDING_AMBIGUOUS 并提示改用内部编号
    await feedbackFinding(finding.finding_id, {
      action: draft.action,
      comment: draft.comment.trim() || undefined,
    })
    notice.value = `风险项 ${finding.finding_id} 已反馈：${draft.action}`
    await refresh()
  } catch (error) {
    loadError.value = error.message
  }
}

// ── 药师干预 → 医师反馈闭环 ──
const interventionText = ref('')
const linkedFindingId = ref('')
const lastIntervention = ref(null)
const responseText = ref('')

async function startIntervention() {
  try {
    lastIntervention.value = await createIntervention(task.value.review_task_id, {
      finding_id: linkedFindingId.value.trim() || undefined,
      intervention_text: interventionText.value.trim(),
    })
    interventionText.value = ''
    linkedFindingId.value = ''
    notice.value = `干预 ${lastIntervention.value.intervention_id} 已发出。`
    await refresh()
  } catch (error) {
    loadError.value = error.message
  }
}

async function answerIntervention(responseType) {
  if (!lastIntervention.value) return
  try {
    lastIntervention.value = await respondIntervention(lastIntervention.value.intervention_id, {
      response_type: responseType,
      response_text: responseText.value.trim() || undefined,
    })
    responseText.value = ''
    notice.value = `干预 ${lastIntervention.value.intervention_id} 已闭环：${responseType}`
    await refresh()
  } catch (error) {
    loadError.value = error.message
  }
}
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">④ 处方审核与风险处理</h2>
      <p class="panel-subtitle">
        确定性规则引擎 · 审核状态与风险等级以业务后端为准
        <span v-if="workflow.reviewTaskNo" class="status-badge status-info" style="margin-left:8px">
          {{ workflow.reviewTaskNo }} · {{ workflow.reviewTaskStatus }}
        </span>
      </p>
    </header>

    <div class="panel-body">
      <!-- 任务获取 -->
      <div class="panel-section">
        <h4>审核任务</h4>
        <div class="row-gap">
          <input v-model="taskIdInput" type="text" class="app-input" placeholder="审核任务号 RV-…" @keyup.enter="refresh()" />
          <button type="button" class="app-button" :disabled="loading" @click="refresh()">查询</button>
          <button
            v-if="workflow.prescriptionNo"
            type="button"
            class="app-button"
            :disabled="loading"
            @click="createTaskForCurrentPrescription"
          >为当前处方建任务</button>
          <button
            v-if="task && isExecutor && task.status === 'created'"
            type="button"
            class="app-button warn"
            :disabled="loading"
            @click="executeRules"
          >
            {{ loading ? '执行中…' : '▶ 执行规则审核' }}
          </button>
          <span v-if="task && !isExecutor && task.status === 'created'" class="status-badge status-muted">执行规则需 service/system_admin 角色</span>
        </div>
        <p v-if="notice" class="success-line">{{ notice }}</p>
        <p v-if="loadError" class="error-line">{{ loadError }}</p>
      </div>

      <!-- 任务详情 -->
      <template v-if="task">
        <div class="panel-section meta-section">
          <div class="kv-row"><span class="kv-key">任务状态</span><span class="kv-value"><span class="status-badge" :class="task.status === 'approved' ? 'status-success' : task.status === 'rejected' ? 'status-high' : task.status === 'superseded' ? 'status-muted' : 'status-warning'">{{ task.status }}</span></span></div>
          <div class="kv-row"><span class="kv-key">规则包版本</span><span class="kv-value mono">{{ task.rule_package_version }}</span></div>
          <div class="kv-row"><span class="kv-key">上下文版本</span><span class="kv-value mono">{{ task.context_version }}</span></div>
          <div class="kv-row"><span class="kv-key">提交时间</span><span class="kv-value">{{ task.submitted_at?.replace('T', ' ').slice(0, 19) }}</span></div>
          <div class="kv-row"><span class="kv-key">药师</span><span class="kv-value">{{ task.assigned_pharmacist_id ?? '未分配' }}</span></div>
        </div>

        <!-- 风险卡片 -->
        <article
          v-for="finding in task.findings"
          :key="`${finding.finding_id}|${finding.rule_code}`"
          class="panel-section finding-card"
          :class="`finding-${severityClass(finding.severity).replace('status-', '')}`"
        >
          <div class="finding-head">
            <span class="finding-icon">{{ SEVERITY_ICON[finding.severity?.toLowerCase()] ?? '🔵' }}</span>
            <span class="status-badge" :class="severityClass(finding.severity)">
              {{ finding.severity?.toUpperCase() }} — 规则 {{ finding.rule_code }} {{ finding.rule_version }}
            </span>
            <span class="status-badge status-muted">动作：{{ ACTION_LABEL[finding.required_action] ?? finding.required_action }}</span>
            <span class="status-badge" :class="finding.finding_status === 'open' ? 'status-warning' : 'status-success'">
              {{ finding.finding_status }}
            </span>
            <small class="finding-no">{{ finding.finding_id }}</small>
          </div>
          <p class="finding-summary">{{ finding.summary }}</p>
          <p v-if="finding.recommendation" class="muted-line">建议：{{ finding.recommendation }}</p>
          <details v-if="finding.evidence" class="evidence-details">
            <summary>知识依据 / 证据</summary>
            <pre>{{ JSON.stringify(finding.evidence, null, 2) }}</pre>
          </details>
          <details class="evidence-details">
            <summary>命中输入快照</summary>
            <pre>{{ JSON.stringify({
              primary_item: finding.primary_prescription_item_id,
              related_items: finding.related_item_ids,
            }, null, 2) }}</pre>
          </details>

          <!-- 医师反馈 -->
          <div v-if="isPhysician && finding.finding_status === 'open'" class="feedback-row">
            <select v-model="draftOf(`${finding.finding_id}|${finding.rule_code}`).action" class="app-select auto">
              <option value="acknowledged">acknowledged 知悉</option>
              <option value="resolved">resolved 已调整</option>
              <option value="overridden">overridden 坚持原方案</option>
            </select>
            <input v-model="draftOf(`${finding.finding_id}|${finding.rule_code}`).comment" type="text" class="app-input" placeholder="反馈说明(可选)" />
            <button type="button" class="app-button" @click="sendFeedback(finding)">反馈</button>
            <button
              type="button"
              class="app-button"
              @click="askAbout({ type: 'review_finding', id: finding.finding_id, title: finding.summary.slice(0, 40), attributes: { severity: finding.severity, rule_code: finding.rule_code } })"
            >问助手</button>
          </div>
        </article>

        <p v-if="!task.findings.length" class="muted-line">
          {{ task.status === 'created' ? '尚未执行规则审核，暂无风险项。' : '本次规则审核未命中任何风险项。' }}
        </p>

        <!-- 药师决定 -->
        <div v-if="isPharmacist && ['system_reviewed', 'pharmacist_reviewing'].includes(task.status)" class="panel-section decide-block">
          <h4>药师审核决定</h4>
          <div class="row-gap wrap">
            <select v-model="decisionType" class="app-select auto">
              <option value="approved">approved 通过</option>
              <option value="intervention_required">intervention_required 需干预</option>
              <option value="rejected">rejected 驳回</option>
            </select>
            <input v-model="signatureRef" type="text" class="app-input auto" placeholder="电子签名引用(可选)" />
          </div>
          <textarea v-model="decisionReason" class="app-textarea compact" rows="2" placeholder="审核理由（驳回/干预建议必填）"></textarea>
          <div class="row-gap">
            <button type="button" class="app-button primary" :disabled="deciding" @click="decide">
              {{ deciding ? '提交中…' : '提交审核决定' }}
            </button>
          </div>
        </div>

        <!-- 药师干预 -->
        <div v-if="isPharmacist && ['system_reviewed', 'pharmacist_reviewing', 'intervention_required'].includes(task.status)" class="panel-section">
          <h4>发起药师干预</h4>
          <textarea v-model="interventionText" class="app-textarea compact" rows="2" placeholder="干预意见，例如：华法林与阿司匹林联用出血风险高，请评估停用阿司匹林…"></textarea>
          <div class="row-gap">
            <input v-model="linkedFindingId" type="text" class="app-input auto" placeholder="关联风险项号 F001(可选)" />
            <button type="button" class="app-button warn" :disabled="!interventionText.trim()" @click="startIntervention">发起干预</button>
          </div>
        </div>

        <!-- 医师答复最近干预（会话内） -->
        <div v-if="lastIntervention && isPhysician" class="panel-section">
          <h4>答复干预 {{ lastIntervention.intervention_id }}（{{ lastIntervention.status }}）</h4>
          <p class="muted-line">“{{ lastIntervention.intervention_text }}”</p>
          <textarea v-model="responseText" class="app-textarea compact" rows="2" placeholder="医师反馈内容(可选)"></textarea>
          <div class="row-gap wrap">
            <button type="button" class="app-button primary" @click="answerIntervention('accepted')">接受</button>
            <button type="button" class="app-button" @click="answerIntervention('partially_accepted')">部分接受</button>
            <button type="button" class="app-button danger" @click="answerIntervention('rejected')">不接受</button>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <span class="empty-icon">🛡️</span>
        <p>在③步提交处方后自动生成审核任务，或粘贴任务号直接查询。<br />风险卡会同时以颜色、图标和文字标注严重程度。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.row-gap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.row-gap.wrap {
  flex-wrap: wrap;
}
.auto {
  width: auto;
  min-width: 140px;
}
.meta-section .kv-row .mono {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
}
.finding-card {
  border-left-width: 3px;
}
.finding-critical, .finding-high { border-left-color: var(--color-danger); }
.finding-warning { border-left-color: var(--color-warm); }
.finding-info { border-left-color: var(--color-info); }
.finding-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.finding-icon {
  font-size: 16px;
}
.finding-no {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: 11px;
}
.finding-summary {
  margin: 10px 0 4px;
  font-size: 14px;
  line-height: 1.65;
}
.evidence-details {
  margin-top: 6px;
}
.evidence-details summary {
  cursor: pointer;
  font-size: 12px;
  color: var(--color-text-secondary);
}
.evidence-details pre {
  margin: 6px 0 0;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  font-size: 11px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 160px;
  overflow-y: auto;
}
.feedback-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border-light);
}
.feedback-row .app-input {
  flex: 1;
}
.decide-block {
  background: var(--color-accent-soft-bg);
  border-color: rgba(45, 212, 191, 0.25);
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
