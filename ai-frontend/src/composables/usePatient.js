import { computed, reactive } from 'vue'
import { getMedicationContext } from '../api/medical'

/**
 * 患者用药上下文（medical-service-backend 为事实来源，前端仅缓存当前会话展示状态）。
 */

const state = reactive({
  patientInput: '',
  loading: false,
  error: '',
  context: null, // MedicationContextData
})

export function usePatient() {
  const patient = state

  const hasPatient = computed(() => Boolean(state.context))

  async function load(patientNo, encounterNo = '') {
    const target = (patientNo ?? '').trim()
    if (!target) {
      state.error = '请输入患者编号。'
      return
    }
    state.loading = true
    state.error = ''
    try {
      state.context = await getMedicationContext(target, encounterNo.trim() || undefined)
      state.patientInput = state.context.patient_id
    } catch (error) {
      state.context = null
      state.error = error.message
      throw error
    } finally {
      state.loading = false
    }
  }

  function reset() {
    state.context = null
    state.error = ''
    state.patientInput = ''
  }

  return { patient: state, hasPatient, load, reset }
}
