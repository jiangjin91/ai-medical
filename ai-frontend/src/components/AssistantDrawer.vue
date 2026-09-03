<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { fetchChatHistory, sendChatMessage } from '../api/assistant'
import { useIdentity } from '../composables/useIdentity'
import { useAssistantContext } from '../composables/useAssistantContext'

const { identity } = useIdentity()
const { assistantFocus, consume } = useAssistantContext()

const expanded = ref(false)
const messages = ref([])
const draft = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const assistantOnline = defineModel('online', { type: String, default: 'idle' }) // idle | open | error

const bodyEl = ref(null)
let currentPageDividerInserted = false

const senderId = computed(() => identity.actorSubject?.trim() || '')

// ── Turn 分组（沿用参考项目结构） ──
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let index = 0
  for (const message of messages.value) {
    if (message.role === 'divider') {
      if (currentTurn) { result.push(currentTurn); currentTurn = null }
      result.push({ type: 'divider', text: message.text })
      continue
    }
    if (message.role === 'user') {
      if (currentTurn) result.push(currentTurn)
      index += 1
      currentTurn = { type: 'turn', id: `turn-${index}`, userMessage: message, botMessages: [] }
    } else {
      if (!currentTurn) {
        index += 1
        currentTurn = { type: 'turn', id: `turn-${index}`, userMessage: null, botMessages: [] }
      }
      currentTurn.botMessages.push(message)
    }
  }
  if (currentTurn) result.push(currentTurn)
  return result
})

async function scrollToBottom() {
  await nextTick()
  const el = bodyEl.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(() => messages.value.length, () => scrollToBottom())

watch(assistantFocus, async (_, oldValue) => {
  // 工作区卡片触发"问助手"：自动展开抽屉并发送对象消息（确定性路由约定，不走意图识别）
  const objectRef = consume()
  if (!objectRef || !senderId.value) return
  expanded.value = true
  appendUserObject(objectRef)
  await dispatch({ object: objectRef })
  void oldValue
})

function createBase(role) {
  return { id: crypto.randomUUID(), role }
}

function insertDividerIfNeeded() {
  if (currentPageDividerInserted || messages.value.length === 0) return
  messages.value.push({ ...createBase('divider'), type: 'divider', text: '以上为历史消息' })
  currentPageDividerInserted = true
}

function appendUserText(text) {
  insertDividerIfNeeded()
  messages.value.push({ ...createBase('user'), type: 'text', text })
}

function appendUserObject(objectRef) {
  insertDividerIfNeeded()
  messages.value.push({ ...createBase('user'), type: 'object', objectType: objectRef.type, payload: objectRef })
}

async function loadHistory() {
  if (!senderId.value) return
  try {
    const history = await fetchChatHistory(senderId.value)
    messages.value = history
      .filter((item) => item.role !== 'divider')
      .map((item) => ({
        ...createBase(item.role === 'user' ? 'user' : 'bot'),
        type: item.object ? 'object' : 'text',
        text: item.text ?? '',
        objectType: item.object?.type,
        payload: item.object,
      }))
    assistantOnline.value = 'open'
    await scrollToBottom()
  } catch (error) {
    assistantOnline.value = 'error'
    errorMessage.value = `${error.message}（工作台功能不受影响）`
  }
}

async function dispatch(payload) {
  isSending.value = true
  errorMessage.value = ''
  try {
    const botMessages = await sendChatMessage(senderId.value, payload)
    for (const message of botMessages) {
      messages.value.push({
        ...createBase('bot'),
        type: message.object ? 'object' : 'text',
        text: message.text ?? '',
        objectType: message.object?.type,
        payload: message.object,
        suggestions: message.suggestions ?? null,
      })
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isSending.value = false
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text) return
  if (!senderId.value) {
    errorMessage.value = '请先在顶部填写操作者主体。'
    return
  }
  draft.value = ''
  appendUserText(text)
  await dispatch({ text })
}

const WELCOME_CHIPS = ['查药品知识', '发起用药推荐', '我的审核任务', '药物相互作用是什么意思']

function objectTitle(payload) {
  const labels = {
    patient: '患者对象',
    prescription: '处方对象',
    medication: '药品对象',
    recommendation: '推荐候选',
    review_finding: '审核风险项',
  }
  return payload.title || labels[payload.type] || '业务对象'
}

onMounted(() => {
  loadHistory()
})
</script>

<template>
  <div class="assistant-root" :class="{ expanded }">
    <button type="button" class="drawer-toggle" @click="expanded = !expanded">
      <span>🤖 合理用药 AI 助手</span>
      <span class="toggle-arrow">{{ expanded ? '▼ 收起' : '▲ 展开' }}</span>
    </button>

    <div v-show="expanded" class="drawer-body">
      <aside class="chat-side">
        <p class="side-tip">自然语言理解由 ai-service-backend 处理；<br />结构化操作请直接使用上方工作台。</p>
        <div class="chips">
          <button
            v-for="chip in WELCOME_CHIPS"
            :key="chip"
            type="button"
            class="chip"
            :disabled="isSending"
            @click="draft = chip; send()"
          >{{ chip }}</button>
        </div>
      </aside>

      <main class="chat-main">
        <div ref="bodyEl" class="messages">
          <template v-for="(item, index) in turns" :key="item.id || index">
            <div v-if="item.type === 'divider'" class="history-divider"><span>{{ item.text }}</span></div>

            <div v-else class="turn-block">
              <div v-if="item.userMessage" class="msg-row user-row">
                <span class="role-tag">医师</span>
                <div v-if="item.userMessage.type === 'object'" class="bubble user-bubble object-mini">
                  📎 {{ objectTitle(item.userMessage.payload) }}
                </div>
                <div v-else class="bubble user-bubble">{{ item.userMessage.text }}</div>
              </div>
              <div v-for="(botMessage, msgIndex) in item.botMessages" :key="msgIndex" class="msg-row bot-row">
                <span class="role-tag bot">助手</span>
                <div v-if="botMessage.type === 'object'" class="bubble bot-bubble object-mini">
                  📎 {{ objectTitle(botMessage.payload) }} · {{ botMessage.payload.id }}
                </div>
                <div v-else class="bubble bot-bubble">{{ botMessage.text }}</div>
              </div>
            </div>
          </template>

          <div v-if="!turns.length" class="welcome-text">
            你好，我是合理用药助手。可以帮你检索药学知识、解释推荐依据与审方风险。
          </div>
        </div>

        <p v-if="errorMessage" class="error-line" style="margin:0 12px 8px">{{ errorMessage }}</p>

        <form class="composer" @submit.prevent="send">
          <input v-model="draft" type="text" class="app-input" placeholder="向助手提问…" :disabled="isSending" />
          <button type="submit" class="app-button primary" :disabled="isSending || !draft.trim()">
            {{ isSending ? '…' : '发送' }}
          </button>
        </form>
      </main>
    </div>
  </div>
</template>

<style scoped>
.assistant-root {
  flex-shrink: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  backdrop-filter: blur(32px) saturate(1.2);
  -webkit-backdrop-filter: blur(32px) saturate(1.2);
  overflow: hidden;
  box-shadow: var(--shadow-md), var(--shadow-inner-glow);
}
.drawer-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  border: none;
  background: transparent;
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.toggle-arrow {
  color: var(--color-text-muted);
  font-size: 12px;
}
.drawer-body {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  border-top: 1px solid var(--color-border-light);
}
.chat-side {
  border-right: 1px solid var(--color-border-light);
  background: var(--color-surface-dim);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.side-tip {
  margin: 0;
  font-size: 11px;
  line-height: 1.7;
  color: var(--color-text-muted);
}
.chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chip {
  padding: 7px 12px;
  border: 1px solid rgba(45, 212, 191, 0.16);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-in-out);
}
.chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
}
.chat-main {
  display: flex;
  flex-direction: column;
  max-height: 340px;
}
.messages {
  flex: 1;
  min-height: 120px;
  max-height: 240px;
  overflow-y: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.history-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border-strong);
}
.turn-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.msg-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.msg-row.user-row { justify-content: flex-end; }
.role-tag {
  flex-shrink: 0;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(56, 189, 248, 0.14);
  color: var(--color-info);
  margin-top: 4px;
}
.role-tag.bot {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.bubble {
  max-width: 78%;
  padding: 8px 13px;
  border-radius: var(--radius-md);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}
.user-bubble {
  background: linear-gradient(135deg, var(--color-accent), var(--color-accent-strong));
  color: #ffffff;
  border-bottom-right-radius: 6px;
}
.bot-bubble {
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  border-top-left-radius: 6px;
}
.object-mini {
  font-size: 12px;
}
.welcome-text {
  margin: auto;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.7;
  text-align: center;
  padding: 20px;
}
.composer {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--color-border-light);
}
.composer .app-button {
  min-width: 72px;
}
@media (max-width: 900px) {
  .drawer-body {
    grid-template-columns: 1fr;
  }
  .chat-side {
    flex-direction: row;
    align-items: center;
    overflow-x: auto;
  }
}
</style>
