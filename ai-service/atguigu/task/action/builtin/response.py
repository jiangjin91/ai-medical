from typing import Any

from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.chat_history.builder import ChatHistoryBuilder
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm_client import llm_client
from atguigu.task.action.base import Action, ActionResult


class ActionResponse(Action):

    name = "action_response"

    async def run(self, action_kwargs: dict[str, Any], dialogue_state: DialogueState) -> ActionResult:
        """
        根据action_kwargs的文本内容，解析占位，封装到ActionResult的messages中BotMessage内容
        职责：响应YAML文件内容（user_flows.yml以及system_flows.yml中的action_response的args中内容展示出来）
        展示的内容注意以下几点：
        1. 展示的结构是什么类型：dict/str
        2. 展示的内容（字符串）：
        2.1 有需要格式化的变量：
            ①：例如 "好的，我们先处理{{ context.started_flow_name }}"。(占位特点是双{{}}占位：jinja2模版)变量名有context
            ②：例如 "订单{{ slots.order_number }}当前状态是：{{ slots.order_status }}。{{ slots.order_summary }}" (占位特点是双{{}}占位：jinja2模版)变量名有slots
        2.2 没有需要格式化的变量： 例如："请简单说一下退款原因"

        `action_response` 是**最重要**、稍微复杂的 action——**几乎所有"对用户说话"都靠它**。它支持三种模式。
            action_kwargs是
            static  只渲染 text 模板  否  文案已写死在 YAML，直接用
            rephrase  渲染 text 后，让 LLM 润色  是  有底稿，但想说得更自然
            generate  直接用 prompt 让 LLM 生成  是
        Args:
            action_kwargs:
            state:

        Returns:

        """
        # 1.获取响应模式
        mode = action_kwargs.get("mode", "static")

        # 2.判断模式
        text = action_kwargs["text"]
        if mode == "static":
            render_text = self._render_text(text, dialogue_state)
            return ActionResult(messages=[BotMessage(text=render_text)])
        elif mode == "rephrase":
            # LLM重写

            # 获取提示词
            prompt = action_kwargs["prompt"]

            # 渲染的文本目标'
            render_text = self._render_text(text, dialogue_state)

            # 调用LLM
            rewriten = await self._call_llm(prompt, dialogue_state, render_text)

            return ActionResult(messages=[BotMessage(text=rewriten)])
        elif mode == "generate":

            # 获取提示词
            prompt = action_kwargs["prompt"]

            # 调用大模型
            rewriten = await self._call_llm(prompt, dialogue_state, render_text="")

            return ActionResult(messages=[BotMessage(text=rewriten)])
        else:
            pass

    def _render_text(self, text: str, dialogue_state: DialogueState) -> str:
        """格式化文本中的变量"""
        template = Template(text)

        return template.render(slots = dialogue_state.active_task.slots if dialogue_state.active_task is not None else None,
                               context = dialogue_state.active_system_task)

    async def _call_llm(self, prompt: str, dialogue_state: DialogueState, render_text: str = "") -> str:
        template = PromptTemplate.from_template(template=prompt)

        chain = template | llm_client | StrOutputParser()

        result = await chain.ainvoke({
            "history": ChatHistoryBuilder.build(dialogue_state.current_session().turns[-5:]),
            "user_message": ChatHistoryBuilder.build_user_message_str(dialogue_state.pending_turn.user_message),
            "current_response": render_text
        })

        return result