<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { createPrescription, getPrescription, submitPrescriptionForReview } from '../api/medical'
import { usePatient } from '../composables/usePatient'
import { useWorkflow } from '../composables/useWorkflow'

const { patient } = usePatient()
const { workflow, applyPrescription, applyReviewTask } = useWorkflow()

// ── 明细编辑 ──
const blankItem = () => ({
  medication_id: '',
  dose_value: '',
  dose_unit: 'mg',
  frequency_code: 'BID',
  frequency_text: '每日两次',
  route_code: 'PO',
  route_text: '口服',
  duration_value: '',
  duration_unit: '天',
  quantity: '',
  quantity_unit: '盒',
  instructions: '',
})
const items = reactive([blankItem()])
const prescriptionType = ref('outpatient')
const creating = ref(false)
const createError = ref('')
const prescription = ref(null)

function addItem() {
  items.push(blankItem())
}
function removeItem(index) {
  if (items.length > 1) items.splice(index, 1)
}

watch(() => patient.context?.patient_id, () => {
  prescription.value = null
  createError.value = ''
  submitError.value = ''
})

async function createDraft() {
  if (!patient.context) {
    createError.value = '请先载入患者上下文。'
    return
  }
  const payloadItems = items
    .filter((item) => String(item.medication_id).trim() && String(item.quantity).trim())
    .map((item) => ({
      medication_id: Number(item.medication_id),
      dose_value: item.dose_value === '' ? undefined : Number(item.dose_value),
      dose_unit: item.dose_unit || undefined,
      frequency_code: item.frequency_code || undefined,
      frequency_text: item.frequency_text,
      route_code: item.route_code || undefined,
      route_text: item.route_text,
      duration_value: item.duration_value === '' ? undefined : Number(item.duration_value),
      duration_unit: item.duration_unit || undefined,
      quantity: Number(item.quantity),
      quantity_unit: item.quantity_unit,
      instructions: item.instructions.trim() || undefined,
    }))
  if (!payloadItems.length) {
    createError.value = '至少填写一条完整明细（药品 ID + 数量）。'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    prescription.value = await createPrescription({
      patient_id: patient.context.patient_id,
      encounter_id: patient.context.encounter_id || undefined,
      prescription_type: prescriptionType.value,
      items: payloadItems,
    })
    applyPrescription(prescription.value)
  } catch (error) {
    createError.value = error.message
  } finally {
    creating.value = false
  }
}

// ── 提交审核 ──
const submitting = ref(false)
const submitError = ref('')

const currentVersion = computed(() => prescription.value?.current_version ?? null)
const versionNo = computed(() => prescription.value?.current_version_no ?? workflow.currentVersionNo ?? 0)

async function submitForReview() {
  if (!prescription.value) return
  submitting.value = true
  submitError.value = ''
  try {
    const task = await submitPrescriptionForReview(prescription.value.prescription_id, {})
    prescription.value.status = 'submitted'
    applyPrescription(prescription.value)
    applyReviewTask(task)
  } catch (error) {
    submitError.value = error.message
  } finally {
    submitting.value = false
  }
}

defineExpose({
  prescriptionId: computed(() => prescription.value?.prescription_id ?? ''),
})
</script>

<template>
  <section class="panel-card">
    <header class="panel-header">
      <h2 class="panel-title">③ 处方草稿与版本</h2>
      <p class="panel-subtitle">
        不可变版本链 · 提交后锁定版本，修改即派生新版本
        <span v-if="workflow.prescriptionNo" class="status-badge status-info" style="margin-left:8px">{{ workflow.prescriptionNo }}</span>
        <span v-if="versionNo" class="status-badge status-muted" style="margin-left:6px">v{{ versionNo }}</span>
      </p>
    </header>

    <div class="panel-body">
      <div class="panel-section">
        <h4>新建处方明细</h4>
        <div class="type-row">
          <label class="field-label inline">处方类型</label>
          <select v-model="prescriptionType" class="app-select" style="width:auto">
            <option value="outpatient">门诊</option>
            <option value="inpatient">住院</option>
            <option value="emergency">急诊</option>
          </select>
        </div>

        <article v-for="(item, index) in items" :key="index" class="rx-item">
          <div class="rx-item-head">
            <span class="rx-no">#{{ index + 1 }}</span>
            <button type="button" class="app-button danger-ghost" @click="removeItem(index)">✕ 移除</button>
          </div>
          <div class="grid-form">
            <label><span>药品 ID *</span><input v-model="item.medication_id" type="text" class="app-input" placeholder="如 3001" /></label>
            <label><span>单次剂量</span><input v-model="item.dose_value" type="text" class="app-input" /></label>
            <label><span>剂量单位</span><input v-model="item.dose_unit" type="text" class="app-input" /></label>
            <label><span>频次编码</span><input v-model="item.frequency_code" type="text" class="app-input" placeholder="QD/BID/TID/QID" /></label>
            <label><span>频次文本 *</span><input v-model="item.frequency_text" type="text" class="app-input" /></label>
            <label><span>途径编码</span><input v-model="item.route_code" type="text" class="app-input" /></label>
            <label><span>途径文本 *</span><input v-model="item.route_text" type="text" class="app-input" /></label>
            <label><span>疗程数值</span><input v-model="item.duration_value" type="text" class="app-input" /></label>
            <label><span>疗程单位</span><input v-model="item.duration_unit" type="text" class="app-input" /></label>
            <label><span>数量 *</span><input v-model="item.quantity" type="text" class="app-input" /></label>
            <label><span>数量单位 *</span><input v-model="item.quantity_unit" type="text" class="app-input" /></label>
            <label class="full"><span>补充说明</span><input v-model="item.instructions" type="text" class="app-input" /></label>
          </div>
        </article>
        <button type="button" class="app-button" @click="addItem">+ 添加药品</button>

        <div class="action-row">
          <button type="button" class="app-button primary" :disabled="creating || !patient.context" @click="createDraft">
            {{ creating ? '创建中…' : '创建处方草稿' }}
          </button>
          <span v-if="!patient.context" class="status-badge status-warning">需先载入患者</span>
        </div>
        <p v-if="createError" class="error-line">{{ createError }}</p>
      </div>

      <!-- 当前版本展示 -->
      <template v-if="prescription">
        <div class="success-line">
          处方 {{ prescription.prescription_id }} 已创建（v{{ prescription.current_version_no }}，状态：{{ prescription.status }}）
        </div>

        <div v-if="currentVersion" class="panel-section">
          <h4>当前版本 v{{ currentVersion.version_no }}（{{ currentVersion.version_status }}）</h4>
          <table class="rx-table">
            <thead>
              <tr><th>#</th><th>药品</th><th>用法用量</th><th>数量</th></tr>
            </thead>
            <tbody>
              <tr v-for="line in currentVersion.items" :key="line.item_id">
                <td>{{ line.item_no }}</td>
                <td>{{ line.medication_name }}<small class="spec">{{ line.specification }}</small></td>
                <td>{{ [line.dose_value && `${line.dose_value}${line.dose_unit ?? ''}`, line.frequency_text, line.route_text].filter(Boolean).join('，') }}</td>
                <td>{{ line.quantity }} {{ line.quantity_unit }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="currentVersion.diagnosis_snapshot?.length" class="muted-line">
            诊断快照：{{ currentVersion.diagnosis_snapshot.map((d) => d.name ?? d.code).join('；') }}
          </p>
        </div>

        <div class="action-row">
          <button
            type="button"
            class="app-button primary"
            :disabled="submitting || prescription.status === 'submitted' || prescription.status === 'approved'"
            @click="submitForReview"
          >
            {{ submitting ? '提交中…' : (prescription.status === 'submitted' ? '已提交审核' : '提交处方审核') }}
          </button>
          <span v-if="prescription.status === 'submitted'" class="status-badge status-success">审核任务：{{ workflow.reviewTaskNo }}</span>
        </div>
        <p v-if="submitError" class="error-line">{{ submitError }}</p>
      </template>
    </div>
  </section>
</template>

<style scoped>
.type-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.field-label.inline {
  margin: 0;
}
.field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}
.rx-item {
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  margin-bottom: 10px;
}
.rx-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.rx-no {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-accent);
}
.grid-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.grid-form label {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.grid-form label span {
  font-size: 11px;
  color: var(--color-text-secondary);
}
.grid-form .full {
  grid-column: span 4;
}
.action-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.danger-ghost {
  border-color: rgba(251, 113, 133, 0.3);
  color: var(--color-danger);
  padding: 4px 10px;
  min-height: 30px;
}
.rx-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rx-table th,
.rx-table td {
  text-align: left;
  padding: 7px 8px;
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: top;
}
.rx-table th {
  color: var(--color-text-secondary);
  font-weight: 600;
}
.spec {
  display: block;
  color: var(--color-text-muted);
  font-size: 11px;
}
@media (max-width: 1600px) {
  .grid-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .grid-form .full {
    grid-column: span 2;
  }
}
</style>
