from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.knowledge.provider.register import KnowledgeRegister
from atguigu.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(self,knowledge_intents: dict[str, KnowledgeIntent],
                 knowledge_register: KnowledgeRegister,
                 knowledgeResponder: KnowledgeResponder):

        self.knowledge_intents = knowledge_intents
        self.knowledge_register = knowledge_register
        self.knowledgeResponder = knowledgeResponder

    async def handle(self, intents: list[str], dialogue_state: DialogueState) -> list[BotMessage]:
        """根据知识意图查询提供者的检索结果，并且通过LLM润色"""

        # 1.根据知识意图查询提供者ID
        provider_ids = self._get_provider_ids_by_intents(intents)

        final_chunks = []
        # 2.根据提供者ID查询提供者对象
        for provider_id in provider_ids:
            provider = self.knowledge_register.get_provider_by_id(provider_id)

            # 3.工具提供者对象查出chunks
            knowledge_chunks = await provider.retrival(dialogue_state)
            final_chunks.extend(knowledge_chunks)

        # 4.将chunks给LLM润色
        bot_messages = await self.knowledgeResponder.response(final_chunks, dialogue_state)
        return bot_messages

    def _get_provider_ids_by_intents(self, intents: list[str]) -> list[str]:
        """根据知识意图查询提供者ID"""
        final_provider_id = []
        for intent in intents:
            knowledge_intent = self.knowledge_intents[intent]
            if knowledge_intent:
                final_provider_id.extend(knowledge_intent.provider_ids)

        return list(set(final_provider_id))

