<script setup>
import { useIdentity } from '../composables/useIdentity'

const { identity, roleLabel, roles, purposes } = useIdentity()

// 助手服务连通状态由 AssistantDrawer 通过 v-model:online 回写
const online = defineModel('online', { type: String, default: 'idle' })
</script>

<template>
  <header class="identity-bar">
    <div class="brand">
      <span class="brand-icon">℞</span>
      <div class="brand-text">
        <h1>合理用药决策支持系统</h1>
        <p>医师 / 药师临床工作台 · 业务事实来源：medical-service-backend</p>
      </div>
    </div>

    <div class="identity-fields">
      <label class="identity-field">
        <span>机构 ID</span>
        <input v-model.number="identity.organizationId" type="number" min="1" class="app-input narrow" />
      </label>
      <label class="identity-field">
        <span>操作者主体</span>
        <input v-model="identity.actorSubject" type="text" placeholder="doc-zhang" class="app-input narrow" />
      </label>
      <label class="identity-field">
        <span>角色</span>
        <select v-model="identity.actorRole" class="app-select narrow">
          <option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option>
        </select>
      </label>
      <label class="identity-field">
        <span>访问目的</span>
        <select v-model="identity.purposeCode" class="app-select narrow">
          <option v-for="purpose in purposes" :key="purpose" :value="purpose">{{ purpose }}</option>
        </select>
      </label>
    </div>

    <div class="bar-status">
      <span class="status-badge status-success">身份：{{ roleLabel }}</span>
      <span
        v-if="online !== 'idle'"
        class="status-badge"
        :class="online === 'open' ? 'status-success' : 'status-high'"
      >
        助手服务{{ online === 'open' ? '在线' : '离线' }}
      </span>
      <span class="hint">生产环境身份应由认证网关注入，此表单仅供联调</span>
    </div>
  </header>
</template>

<style scoped>
.identity-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  backdrop-filter: blur(32px) saturate(1.2);
  -webkit-backdrop-filter: blur(32px) saturate(1.2);
  box-shadow: var(--shadow-glow-teal), var(--shadow-md), var(--shadow-inner-glow);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-accent), #0d9488);
  color: #ffffff;
  font-size: 22px;
  font-weight: 700;
  box-shadow: 0 6px 18px var(--color-accent-glow);
}
.brand-text h1 {
  margin: 0;
  font-size: 17px;
  letter-spacing: -0.01em;
  white-space: nowrap;
  background: linear-gradient(135deg, #f0ede6 0%, var(--color-accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.brand-text p {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.identity-fields {
  flex: 1;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  min-width: 0;
}
.identity-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.identity-field > span {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}
.narrow.app-input,
.narrow.app-select {
  width: 140px;
  min-height: 34px;
  padding: 6px 10px;
  font-size: 13px;
}

.bar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.bar-status .hint {
  font-size: 11px;
  color: var(--color-text-muted);
  max-width: 150px;
  line-height: 1.4;
}

@media (max-width: 1420px) {
  .identity-bar {
    flex-wrap: wrap;
  }
  .narrow.app-input,
  .narrow.app-select {
    width: 120px;
  }
}
</style>
