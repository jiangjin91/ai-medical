from langchain_core.output_parsers import StrOutputParser

from atguigu.chat_history.builder import ChatHistoryBuilder
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm_client import llm_client
from atguigu.prompt.loader import load_prompt_template_content
from langchain_core.prompts import PromptTemplate

class ChitChatResponder:

    async def response(self, chat: str, dialogue_state: DialogueState) -> list[BotMessage]:
        """调用大模型"""

        # 1.加载提示词内容
        prompt_content = load_prompt_template_content("chitchat_respond")

        # 2.加载模板
        template = PromptTemplate.from_template(template=prompt_content, template_format="jinja2")

        # 3.定义chain
        chain = template | llm_client | StrOutputParser()

        result = await chain.ainvoke({
            "history":ChatHistoryBuilder.build(dialogue_state.current_session().turns[-10:]),
            "user_message":chat,
        })

        return [BotMessage(text=result)]

