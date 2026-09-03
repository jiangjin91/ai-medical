from requests import session

from atguigu.chat_history.builder import ChatHistoryBuilder
from atguigu.domain.messages import UserMessage, ProcessedResult, ChatHistoryMessage
from atguigu.engines.dialogue_engine import DialogueEngine
from atguigu.repository.dialogue_repository import DialogueRepository


class DialogueStateService:

    def __init__(self, engine: DialogueEngine, repository: DialogueRepository):
        self._engine = engine
        self._repository = repository


    async def process_message(self, user_message: UserMessage) -> ProcessedResult:
        """处理对话消息的核心入口"""

        # 1.从数据库中读取当前用户的对话状态 I/O
        dialogue_state = await self._repository.load_state(user_message.sender_id)

        # 2.引擎层使用（修改对话状态中的内容）
        processed_result = await self._engine.handle_message(user_message, dialogue_state)

        # 3.修改后的对话状态内容保存到数据库中 I/O
        await self._repository.save_state(user_message.sender_id,dialogue_state)

        # 擎的返回值 `ProcessResult` 只装"这一轮要回复什么"，不装状态。
        return processed_result

    async def get_chat_history(self, sender_id: str) -> list[ChatHistoryMessage]:
        """查询该用户下的历史消息"""

        state = await self._repository.load_state(sender_id)

        chat_history_messages = []
        for session in state.sessions:
            session_id = session.session_id
            for turn in session.turns:
                user_message = turn.user_message
                user_history = ChatHistoryBuilder.build_chat_history(session_id=session_id, role="user", text=user_message.text,
                                                                object=user_message.object)
                chat_history_messages.append(user_history)
                for bot_message in turn.bot_messages:
                    bot_history = ChatHistoryBuilder.build_chat_history(session_id, "bot", bot_message.text,
                                                                    bot_message.object)
                    chat_history_messages.append(bot_history)

        return chat_history_messages
