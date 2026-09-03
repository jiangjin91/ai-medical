import { computed, reactive, watch } from 'vue'

/**
 * 开发阶段身份上下文。
 * 生产环境这些字段应由认证网关从令牌注入，页面表单仅用于本地联调模拟网关注入行为。
 * 只保存身份配置，不保存任何患者/处方等业务数据（遵守职责文档 5.3 数据安全约束）。
 */

const ROLES = [
  { value: 'physician', label: '医师', hint: '病情确认 · 推荐 · 处方 · 风险反馈' },
  { value: 'pharmacist', label: '药师', hint: '审方决定 · 药师干预' },
  { value: 'review_pharmacist', label: '审核药师', hint: '审方决定 · 药师干预' },
  { value: 'service', label: '系统服务', hint: '执行规则审核' },
  { value: 'system_admin', label: '系统管理员', hint: '全部操作 + 规则管理' },
]

const PURPOSES = ['treatment', 'medication_review', 'knowledge_query', 'audit']

const STORAGE_KEY = 'medical_workbench_identity'

function loadPersisted() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch (_) {
    return null
  }
}

const persisted = loadPersisted()

const state = reactive({
  organizationId: persisted?.organizationId ?? 1,
  actorSubject: persisted?.actorSubject ?? 'idp-user-201',
  actorRole: persisted?.actorRole ?? 'physician',
  purposeCode: persisted?.purposeCode ?? 'treatment',
})

watch(
  () => ({ ...state }),
  (value) => {
    // 身份配置不属于敏感患者数据，允许会话级缓存
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value)) } catch (_) { /* ignore */ }
  },
)

export function useIdentity() {
  const identity = state

  const roleLabel = computed(
    () => ROLES.find((r) => r.value === state.actorRole)?.label ?? state.actorRole,
  )

  function headers() {
    if (!state.organizationId || !state.actorSubject || !state.actorRole || !state.purposeCode) {
      throw new Error('请先在顶部配置完整身份信息（机构 / 操作者 / 角色 / 访问目的）。')
    }
    return {
      'X-Organization-ID': String(state.organizationId),
      'X-Actor-Subject': state.actorSubject,
      'X-Actor-Role': state.actorRole,
      'X-Purpose-Code': state.purposeCode,
      'X-Correlation-ID': crypto.randomUUID(),
    }
  }

  function hasAnyRole(allowed) {
    return allowed.includes(state.actorRole)
  }

  return { identity, roleLabel, roles: ROLES, purposes: PURPOSES, headers, hasAnyRole }
}
