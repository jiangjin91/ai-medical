import { reactive } from 'vue'

/**
 * 工作区 → AI 助手的对象传递通道。
 * 业务卡片点击"问助手"时设置 focus 对象，AssistantDrawer 监听并发送 object 消息。
 * type 取值约定见 ai-service-backend-plan：patient/prescription/medication/recommendation/review_finding。
 */

const state = reactive({
  pendingObject: null, // { id, title, type, attributes }
  sequence: 0,         // 触发 watcher 用（相同对象重复发送）
})

export function useAssistantContext() {
  function askAbout(objectRef) {
    if (!objectRef?.id && !objectRef?.title) return
    state.pendingObject = objectRef
    state.sequence += 1
  }

  function consume() {
    const obj = state.pendingObject
    state.pendingObject = null
    return obj
  }

  return { assistantFocus: state, askAbout, consume }
}
