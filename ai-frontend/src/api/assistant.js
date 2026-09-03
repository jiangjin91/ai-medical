/**
 * ai-service-backend 对话接口封装（仅自然语言理解走 AI 后端）。
 * 经 vite 代理 /api → http://127.0.0.1:18082。
 */
import { useIdentity } from '../composables/useIdentity'

export async function fetchChatHistory(senderId) {
  const { headers } = useIdentity()
  const response = await fetch(`/api/chat/history?sender_id=${encodeURIComponent(senderId)}`, {
    headers: headers(),
  })
  let payload = null
  try { payload = await response.json() } catch (_) { /* ignore */ }
  if (!response.ok) {
    throw new Error(payload?.detail || `加载历史消息失败（HTTP ${response.status}）`)
  }
  return Array.isArray(payload?.messages) ? payload.messages : []
}

export async function sendChatMessage(senderId, { text, object } = {}) {
  if (!text && !object) {
    throw new Error('消息内容为空。')
  }
  let response
  try {
    const { headers } = useIdentity()
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...headers() },
      body: JSON.stringify({
        sender_id: senderId,
        text: text ?? null,
        object: object ?? null,
      }),
    })
  } catch (error) {
    throw new Error('无法连接智能助手服务，请确认 ai-service-backend 已启动。')
  }

  let payload = null
  try { payload = await response.json() } catch (_) { /* ignore */ }
  if (!response.ok) {
    throw new Error(payload?.detail || `请求失败（HTTP ${response.status}）`)
  }
  return Array.isArray(payload?.messages) ? payload.messages : []
}
