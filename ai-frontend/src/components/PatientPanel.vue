<script setup>
import { ref } from 'vue'
import { usePatient } from '../composables/usePatient'

const { patient, load } = usePatient()

const encounterInput = ref('')
const inputError = ref('')

async function loadContext() {
  inputError.value = ''
  try {
    await load(patient.patientInput, encounterInput.value)
  } catch (_) {
    // 错误已写入 patient.error
  }
}

function severityClass(value) {
  if (!value) return 'status-muted'
  const normalized = value.toLowerCase()
  if (['severe', 'critical'].includes(normalized)) return 'status-critical'
  if (normalized === 'high') return 'status-high'
  if (normalized === 'moderate' || normalized === 'warning') return 'status-warning'
  if (normalized === 'mild' || normalized === 'info') return 'status-info'
  return 'status-muted'
}

function formatDate(value) {
  if (!value) return '—'
  return String(value).slice(0, 10)
}
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">患者用药上下文</h2>
      <p class="panel-subtitle">诊断 · 过敏史 · 当前用药 · 检验（机构隔离 + 脱敏）</p>
    </header>

    <div class="selector">
      <input
        v-model="patient.patientInput"
        type="text"
        class="app-input"
        placeholder="患者编号，如 PAT-2024-00001"
        @keyup.enter="loadContext"
      />
      <input
        v-model="encounterInput"
        type="text"
        class="app-input encounter"
        placeholder="就诊号(可选)"
        @keyup.enter="loadContext"
      />
      <button type="button" class="app-button primary" :disabled="patient.loading" @click="loadContext">
        {{ patient.loading ? '查询中…' : '载入' }}
      </button>
    </div>
    <p class="sample-hint">测试编号：PAT-2024-00001 ~ PAT-2024-00005</p>

    <p v-if="patient.error" class="error-line">{{ patient.error }}</p>

    <div v-if="patient.context" class="panel-body context-body">
      <!-- 数据质量 -->
      <div class="panel-section quality-section">
        <h4>数据质量标记</h4>
        <div class="quality-row">
          <span
            v-for="field in patient.context.data_quality.missing_fields"
            :key="`miss-${field}`"
            class="status-badge status-warning"
          >⚠ 缺失:{{ field }}</span>
          <span
            v-for="field in patient.context.data_quality.stale_fields"
            :key="`stale-${field}`"
            class="status-badge status-info"
          >⏱ 过期:{{ field }}</span>
          <span
            v-if="!patient.context.data_quality.missing_fields.length && !patient.context.data_quality.stale_fields.length"
            class="status-badge status-success"
          >✓ 资料完整</span>
        </div>
      </div>

      <!-- 基本信息 -->
      <div class="panel-section">
        <h4>基本信息</h4>
        <div class="kv-row"><span class="kv-key">患者编号</span><span class="kv-value">{{ patient.context.patient_id }}</span></div>
        <div class="kv-row"><span class="kv-key">年龄/性别</span><span class="kv-value">{{ patient.context.demographics.age }} 岁 / {{ patient.context.demographics.sex }}</span></div>
        <div class="kv-row"><span class="kv-key">出生日期</span><span class="kv-value">{{ formatDate(patient.context.demographics.birth_date) }}</span></div>
        <div class="kv-row"><span class="kv-key">上下文版本</span><span class="kv-value mono">{{ patient.context.context_version }}</span></div>
        <div class="kv-row">
          <span class="kv-key">特殊人群</span>
          <span class="kv-value flags">
            <span v-if="patient.context.special_population.pediatric" class="status-badge status-warning">儿童</span>
            <span v-if="patient.context.special_population.older_adult" class="status-badge status-warning">老年 ≥65</span>
            <span v-if="patient.context.special_population.pregnancy_status === 'unknown'" class="status-badge status-warning">妊娠未知</span>
            <span
              v-if="!patient.context.special_population.pediatric && !patient.context.special_population.older_adult && patient.context.special_population.pregnancy_status !== 'unknown'"
              class="status-badge status-muted"
            >无特殊标记</span>
          </span>
        </div>
      </div>

      <!-- 过敏史 -->
      <div class="panel-section" :class="{ 'alert-section': patient.context.allergies.length > 0 }">
        <h4>过敏史（{{ patient.context.allergies.length }}）</h4>
        <p v-if="!patient.context.allergies.length" class="muted-line">未记录过敏史——请与患者口头确认。</p>
        <ul v-else class="item-list">
          <li v-for="(allergy, index) in patient.context.allergies" :key="index" class="item-line allergy-line">
            <span class="status-badge status-high">过敏</span>
            <div class="item-text">
              <strong>{{ allergy.allergen_name }}</strong>
              <small>{{ allergy.allergen_type }}<template v-if="allergy.severity"> · 严重程度 {{ allergy.severity }}</template> · {{ allergy.verification_status }}</small>
            </div>
          </li>
        </ul>
      </div>

      <!-- 诊断 -->
      <div class="panel-section">
        <h4>诊断（{{ patient.context.diagnoses.length }}）</h4>
        <p v-if="!patient.context.diagnoses.length" class="muted-line">暂无有效诊断。</p>
        <ul v-else class="item-list">
          <li v-for="(diagnosis, index) in patient.context.diagnoses" :key="index" class="item-line">
            <span class="status-badge" :class="diagnosis.diagnosis_type === 'primary' ? 'status-success' : 'status-muted'">{{ diagnosis.diagnosis_type === 'primary' ? '主诊断' : diagnosis.diagnosis_type === 'secondary' ? '次诊断' : '病史' }}</span>
            <div class="item-text">
              <strong>{{ diagnosis.name }}</strong>
              <small>{{ diagnosis.code }}<template v-if="diagnosis.system"> · {{ diagnosis.system }}</template> · {{ diagnosis.confirmation_status }}</small>
            </div>
          </li>
        </ul>
      </div>

      <!-- 当前用药 -->
      <div class="panel-section">
        <h4>当前用药（{{ patient.context.current_medications.length }}）</h4>
        <p v-if="!patient.context.current_medications.length" class="muted-line">当前无在用药物。</p>
        <ul v-else class="item-list">
          <li v-for="(medication, index) in patient.context.current_medications" :key="index" class="item-line">
            <span class="status-badge status-success">在用</span>
            <div class="item-text">
              <strong>{{ medication.medication_name }}</strong>
              <small>{{ medication.dosage || '剂量不详' }} · {{ medication.route || '途径不详' }} · {{ medication.frequency || '频次不详' }}</small>
            </div>
          </li>
        </ul>
      </div>

      <!-- 近期检验 -->
      <div class="panel-section">
        <h4>近期检验（{{ patient.context.recent_observations.length }}）</h4>
        <p v-if="!patient.context.recent_observations.length" class="muted-line">暂无检验记录。</p>
        <ul v-else class="item-list">
          <li v-for="(observation, index) in patient.context.recent_observations.slice(0, 8)" :key="index" class="item-line">
            <span class="status-badge" :class="observation.abnormal_flag && observation.abnormal_flag !== 'normal' ? severityClass(observation.abnormal_flag) : 'status-muted'">
              {{ observation.abnormal_flag === 'normal' ? '正常' : (observation.abnormal_flag || '见报告') }}
            </span>
            <div class="item-text">
              <strong>{{ observation.name }}</strong>
              <small>
                {{ [observation.value_numeric ?? observation.value_text, observation.unit].filter(Boolean).join(' ') || '—' }}
                <template v-if="observation.reference_range">（参考 {{ observation.reference_range }}）</template>
              </small>
            </div>
          </li>
        </ul>
      </div>

      <!-- 不良反应史 -->
      <div class="panel-section">
        <h4>不良反应史（{{ patient.context.adverse_reactions.length }}）</h4>
        <p v-if="!patient.context.adverse_reactions.length" class="muted-line">未记录不良反应。</p>
        <ul v-else class="item-list">
          <li v-for="(reaction, index) in patient.context.adverse_reactions" :key="index" class="item-line">
            <span class="status-badge" :class="severityClass(reaction.severity)">ADR</span>
            <div class="item-text">
              <strong>{{ reaction.medication_name }}</strong>
              <small>{{ reaction.reaction }}</small>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <div v-else-if="!patient.error && !patient.loading" class="empty-state">
      <span class="empty-icon">🩺</span>
      <p>输入患者编号并载入，开始本次合理用药工作流。</p>
    </div>
  </section>
</template>

<style scoped>
.selector {
  display: flex;
  gap: 8px;
  padding: 12px 14px 4px;
}
.selector .app-input:first-child {
  flex: 1;
}
.selector .encounter {
  width: 110px;
  flex-shrink: 0;
}
.sample-hint {
  margin: 6px 16px 10px;
  font-size: 11px;
  color: var(--color-text-muted);
}

.panel-card {
  height: 100%;
}
.context-body {
  padding-top: 0;
}

.quality-section .quality-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.alert-section {
  border-color: rgba(251, 113, 133, 0.35);
  background: rgba(251, 113, 133, 0.06);
}

.item-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.item-line .status-badge {
  margin-top: 2px;
  flex-shrink: 0;
}
.item-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.item-text strong {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}
.item-text small {
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.flags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}
.mono {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 30px 20px;
  text-align: center;
}
.empty-icon {
  font-size: 40px;
  opacity: 0.5;
}
.empty-state p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.7;
}
</style>
