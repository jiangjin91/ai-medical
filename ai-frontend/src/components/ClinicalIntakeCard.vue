<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { createClinicalIntake, confirmClinicalIntake } from '../api/medical'
import { usePatient } from '../composables/usePatient'
import { useWorkflow } from '../composables/useWorkflow'

const { patient } = usePatient()
const { workflow, startIntake, applyAssessment, switchStep } = useWorkflow()

// ── 第一步：录入病情描述，保存结构化草稿 ──
const rawDescription = ref('')
const sourceType = ref('clinician_entered')
const saving = ref(false)
const saveError = ref('')
const saveSuccess = ref('')

async function saveDraft() {
  if (!patient.context) {
    saveError.value = '请先在左侧载入患者用药上下文。'
    return
  }
  const description = rawDescription.value.trim()
  if (!description) {
    saveError.value = '请填写患者的病情描述或主诉。'
    return
  }
  saving.value = true
  saveError.value = ''
  saveSuccess.value = ''
  try {
    const intake = await createClinicalIntake({
      patient_id: patient.context.patient_id,
      encounter_id: patient.context.encounter_id || undefined,
      source_type: sourceType.value,
      raw_description: description,
    })
    startIntake(intake.intake_id, intake.status, intake.emergency_screen_result)
    saveSuccess.value = `草稿已保存：${intake.intake_id}`
  } catch (error) {
    saveError.value = error.message
  } finally {
    saving.value = false
  }
}

// ── 第二步：医师确认（生成临床评估） ──
const summaryText = ref('')
const extraDiagnosisLines = ref('')
const confirming = ref(false)
const confirmError = ref('')

// 默认全选患者档案中的有效诊断；医师可反选或补充
const checkedDiagnoses = reactive(new Set())

const draftActive = computed(() => Boolean(workflow.intakeNo) && workflow.intakeStatus === 'awaiting_confirmation')
const assessmentDone = computed(() => Boolean(workflow.assessmentNo))

function toggleDiagnosis(diagnosis) {
  const key = `${diagnosis.code}|${diagnosis.name}|${diagnosis.diagnosis_type}`
  if (checkedDiagnoses.has(key)) checkedDiagnoses.delete(key)
  else checkedDiagnoses.add(key)
}

// 患者上下文变化时重置勾选并预填全部档案诊断
watch(
  () => patient.context?.patient_id,
  () => {
    checkedDiagnoses.clear()
    summaryText.value = ''
    extraDiagnosisLines.value = ''
    ;(patient.context?.diagnoses ?? []).forEach((item) => {
      checkedDiagnoses.add(`${item.code}|${item.name}|${item.diagnosis_type}`)
    })
  },
)

const confirmedDiagnoses = computed(() => {
  const items = []
  for (const key of checkedDiagnoses) {
    const [code, name, type] = key.split('|')
    items.push({ code, name, type })
  }
  for (const line of extraDiagnosisLines.value.split('\n')) {
    const [code, name, type] = line.trim().split('|').map((part) => part?.trim())
    if (code && name) items.push({ code, name, type: type || 'secondary' })
  }
  return items
})

async function confirm() {
  if (!draftActive.value) return
  const text = summaryText.value.trim()
  if (!text) {
    confirmError.value = '请填写医师确认的临床摘要。'
    return
  }
  if (!confirmedDiagnoses.value.length) {
    confirmError.value = '至少选择或补充一条确认诊断。'
    return
  }
  confirming.value = true
  confirmError.value = ''
  try {
    const assessment = await confirmClinicalIntake(workflow.intakeNo, {
      summary: text,
      confirmed_diagnoses: confirmedDiagnoses.value,
      confirmed_context: {
        source_intake: workflow.intakeNo,
        confirmed_by_subject: undefined,
      },
    })
    applyAssessment(assessment)
    switchStep('recommendation')
  } catch (error) {
    confirmError.value = error.message
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">① 病情描述与医师确认</h2>
      <p class="panel-subtitle">
        模型提取内容未经医师确认不得视为临床结论 · 紧急风险触发时禁止进入推荐
        <span v-if="workflow.intakeNo" class="status-badge" :class="assessmentDone ? 'status-success' : 'status-warning'" style="margin-left:8px">
          {{ workflow.intakeNo }}
        </span>
      </p>
    </header>

    <div class="panel-body">
      <!-- 录入 -->
      <div class="panel-section">
        <h4>原始描述 / 医师主诉</h4>
        <div class="row-gap">
          <select v-model="sourceType" class="app-select narrow-field">
            <option value="clinician_entered"> clinician_entered（医师录入）</option>
            <option value="patient_reported">patient_reported（患者自述）</option>
          </select>
        </div>
        <textarea
          v-model="rawDescription"
          class="app-textarea"
          rows="4"
          placeholder="例如：患者近一周反复心悸，伴轻度胸闷，活动后加重，无胸痛放射…"
        ></textarea>
        <div class="action-row">
          <button type="button" class="app-button primary" :disabled="saving || !rawDescription.trim()" @click="saveDraft">
            {{ saving ? '保存中…' : '保存临床资料草稿' }}
          </button>
          <span v-if="saveSuccess" class="status-badge status-success">{{ saveSuccess }}</span>
        </div>
        <p v-if="saveError" class="error-line">{{ saveError }}</p>
      </div>

      <!-- 紧急提示 -->
      <p v-if="workflow.emergencyTriggered" class="error-line emergency">
        🚨 紧急风险筛查已触发（{{ workflow.intakeNo }}）：必须先按急诊流程处理，系统已阻止确认与推荐入口。
      </p>

      <!-- 确认 -->
      <div v-if="draftActive" class="panel-section confirm-section">
        <h4>医师确认（{{ workflow.intakeNo }}）</h4>
        <label class="field-label">临床摘要（医师核定表述）</label>
        <textarea
          v-model="summaryText"
          class="app-textarea"
          rows="3"
          placeholder="医师复核后的正式临床摘要…"
        ></textarea>

        <label class="field-label">确认诊断（来自患者档案，可取消勾选）</label>
        <div class="diagnosis-choices">
          <label v-for="(diagnosis, index) in patient.context?.diagnoses ?? []" :key="index" class="choice-item">
            <input
              type="checkbox"
              :checked="checkedDiagnoses.has(`${diagnosis.code}|${diagnosis.name}|${diagnosis.diagnosis_type}`)"
              @change="toggleDiagnosis(diagnosis)"
            />
            <span>{{ diagnosis.name }}（{{ diagnosis.code }}）</span>
          </label>
          <p v-if="!(patient.context?.diagnoses ?? []).length" class="muted-line">患者档案暂无诊断，请在下方手动补充。</p>
        </div>

        <label class="field-label">补充新诊断（每行一条，格式：编码|名称|类型 primary/secondary/history）</label>
        <textarea
          v-model="extraDiagnosisLines"
          class="app-textarea compact"
          rows="2"
          placeholder="I48.0|心房颤动|primary"
        ></textarea>

        <div class="action-row">
          <button
            type="button"
            class="app-button primary"
            :disabled="confirming || !summaryText.trim()"
            @click="confirm"
          >
            {{ confirming ? '确认中…' : '确认并生成临床评估' }}
          </button>
        </div>
        <p v-if="confirmError" class="error-line">{{ confirmError }}</p>
      </div>

      <div v-else-if="assessmentDone" class="success-line">
        ✓ 临床评估已完成：{{ workflow.assessmentNo }}（context_version={{ workflow.contextVersion || '—' }}），可进入第②步发起推荐。
      </div>
    </div>
  </section>
</template>

<style scoped>
.row-gap {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}
.narrow-field {
  width: auto;
  min-width: 240px;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.confirm-section {
  border-color: rgba(45, 212, 191, 0.25);
  background: var(--color-accent-soft-bg);
}
.field-label {
  display: block;
  margin: 12px 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.compact {
  min-height: 52px;
}
.diagnosis-choices {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.choice-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
}
.emergency {
  animation: blink 1.6s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.72; }
}
</style>
