import { useIdentity } from '../composables/useIdentity'

/**
 * medical-service-backend 业务接口封装。
 * 所有请求经 vite 代理 /business → medical-service-backend（/api/v1/*）。
 * 统一注入身份请求头；统一解包 {code,message,data}；错误抛出 Error(message)，err.code 为业务错误码。
 */

const BASE = '/business/api/v1'

export class MedicalApiError extends Error {
  constructor(message, code, status) {
    super(message)
    this.name = 'MedicalApiError'
    this.code = code
    this.status = status
  }
}

function correlationId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `cid-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

async function request(path, { method = 'GET', body, query, contextHeaders } = {}) {
  const { headers } = useIdentity()
  // 支持调用方覆盖身份头（例如切换角色后重试同一步骤）
  const identityHeaders = contextHeaders ?? headers()

  let url = `${BASE}${path}`
  if (query) {
    const qs = new URLSearchParams(
      Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ''),
    )
    const encoded = qs.toString()
    if (encoded) url += `?${encoded}`
  }

  let response
  try {
    response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...identityHeaders,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    throw new MedicalApiError('无法连接业务服务，请确认 medical-service-backend 已启动。', 'NETWORK_ERROR', 0)
  }

  // 统一响应包装：{code,message,data}
  let payload = null
  try { payload = await response.json() } catch (_) { /* 非 JSON 错误体 */ }

  if (!response.ok) {
    // FastAPI 校验错误（422）与业务错误（detail.code/message）两种形态
    const detail = payload?.detail
    if (Array.isArray(detail)) {
      const first = detail[0]
      throw new MedicalApiError(
        `参数校验失败：${first?.msg ?? '请求参数不合法'}（${(first?.loc ?? []).join('.')}）`,
        'VALIDATION_ERROR',
        response.status,
      )
    }
    throw new MedicalApiError(
      detail?.message ?? payload?.detail ?? payload?.message ?? `请求失败（HTTP ${response.status}）`,
      detail?.code ?? 'REQUEST_FAILED',
      response.status,
    )
  }

  return payload?.data !== undefined ? payload.data : payload
}

// ── 患者上下文 ──────────────────────────────────────────────

export function getMedicationContext(patientId, encounterId) {
  return request(`/patients/${encodeURIComponent(patientId)}/medication-context`, {
    query: { encounter_id: encounterId },
  })
}

export function getEncounter(encounterId) {
  return request(`/encounters/${encodeURIComponent(encounterId)}`)
}

// ── 药品与知识 ──────────────────────────────────────────────

export function getMedication(medicationId) {
  return request(`/medications/${encodeURIComponent(medicationId)}`)
}

export function searchKnowledge({ q = '', entryType, medicationId, page = 1, pageSize = 20 }) {
  return request('/knowledge/search', {
    query: { q, entry_type: entryType, medication_id: medicationId, page, page_size: pageSize },
  })
}

// ── 临床资料 ────────────────────────────────────────────────

export function createClinicalIntake(payload) {
  return request('/clinical-intakes', { method: 'POST', body: payload })
}

export function getClinicalIntake(intakeId) {
  return request(`/clinical-intakes/${encodeURIComponent(intakeId)}`)
}

export function confirmClinicalIntake(intakeId, payload) {
  return request(`/clinical-intakes/${encodeURIComponent(intakeId)}/confirm`, { method: 'POST', body: payload })
}

// ── 用药推荐 ────────────────────────────────────────────────

export function createRecommendation(payload) {
  return request('/medication-recommendations', { method: 'POST', body: payload })
}

export function getRecommendation(recommendationId) {
  return request(`/medication-recommendations/${encodeURIComponent(recommendationId)}`)
}

export function decideRecommendation(recommendationId, payload) {
  return request(`/medication-recommendations/${encodeURIComponent(recommendationId)}/decisions`, {
    method: 'POST',
    body: payload,
  })
}

// ── 处方 ────────────────────────────────────────────────────

export function createPrescription(payload) {
  return request('/prescriptions', { method: 'POST', body: payload })
}

export function getPrescription(prescriptionId) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}`)
}

export function createPrescriptionVersion(prescriptionId, payload) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/versions`, {
    method: 'POST',
    body: payload,
  })
}

export function submitPrescriptionForReview(prescriptionId, payload = {}) {
  return request(`/prescriptions/${encodeURIComponent(prescriptionId)}/submit-for-review`, {
    method: 'POST',
    body: payload,
  })
}

// ── 处方审核 ────────────────────────────────────────────────

export function createReviewTask(payload) {
  return request('/review-tasks', { method: 'POST', body: payload })
}

export function getReviewTask(taskId) {
  return request(`/review-tasks/${encodeURIComponent(taskId)}`)
}

export function executeReviewTask(taskId) {
  return request(`/review-tasks/${encodeURIComponent(taskId)}/execute`, { method: 'POST' })
}

export function decideReviewTask(taskId, payload) {
  return request(`/review-tasks/${encodeURIComponent(taskId)}/decisions`, { method: 'POST', body: payload })
}

export function feedbackFinding(findingId, payload) {
  return request(`/findings/${encodeURIComponent(findingId)}/feedback`, { method: 'POST', body: payload })
}

export function createIntervention(taskId, payload) {
  return request(`/review-tasks/${encodeURIComponent(taskId)}/interventions`, { method: 'POST', body: payload })
}

export function respondIntervention(interventionId, payload) {
  return request(`/interventions/${encodeURIComponent(interventionId)}/respond`, { method: 'POST', body: payload })
}

// ── 规则 ────────────────────────────────────────────────────

export function getRule(ruleId) {
  return request(`/rules/${encodeURIComponent(ruleId)}`)
}

export { correlationId }
