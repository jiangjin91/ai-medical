from langchain_core.output_parsers import StrOutputParser

from atguigu.chat_history.builder import ChatHistoryBuilder
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm_client import llm_client
from atguigu.knowledge.provider.provider import KnowledgeChunk
from atguigu.prompt.loader import load_prompt_template_content
from langchain_core.prompts import PromptTemplate


class KnowledgeResponder:

    async def response(self,
                       knowledge_chunks: list[KnowledgeChunk],
                       dialogue_state: DialogueState
                       ) -> list[BotMessage]:
        """调用大模型"""

        # 1.加载提示词内容
        prompt_content = load_prompt_template_content("knowledge_respond")
        # 2.定义提示词模板对象
        template = PromptTemplate.from_template(template=prompt_content, template_format="jinja2")

        # 3.定义chain
        chain = template | llm_client | StrOutputParser()

        # 4.调用链
        result = await chain.ainvoke({
            "user_message":ChatHistoryBuilder.build_user_message_str(dialogue_state.pending_turn.user_message),
            "history":ChatHistoryBuilder.build(dialogue_state.current_session().turns[-10:]),
            "knowledge_content": "\n\n".join([chunk.content for chunk in knowledge_chunks]),
        })

        return [BotMessage(text=result)]