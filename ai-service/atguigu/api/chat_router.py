"""
定义路由
"""
import uuid
from fastapi import APIRouter, Depends

from atguigu.api.dependendies import DialogueStateServiceDep
from atguigu.api.schemas import ChatResponse, ChatRequest, ChatBotMessage, ChatObject, ChatHistoryResponse
from atguigu.domain.messages import UserMessage, MessageType, FocusedObject, ProcessedResult

# 创建实例
router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, service: DialogueStateServiceDep):

    # 1.将接口数据转换成领域数据模型
    user_message = _build_user_message(chat_request)

    # 2.调用service处理领域数据模型---返回的还是领域数据模型
    processed_result = await service.process_message(user_message)

    # 3.将处理后的领域数据模型转换成接口数据模型
    chat_response = _build_chat_response(processed_result)

    return chat_response

def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    """将接口数据类型转换成领域数据模型"""
    return UserMessage(
        sender_id = chat_request.sender_id,
        message_id = str(uuid.uuid4().hex),
        type = MessageType.OBJECT if chat_request.object is not None else MessageType.TEXT,
        text = chat_request.text,
        object = FocusedObject(
            id = chat_request.object.id,
            title = chat_request.object.title,
            type = chat_request.object.type,
            attributes = chat_request.object.attributes
        ) if chat_request.object is not None else None
    )


def _build_chat_response(processed_result: ProcessedResult) -> ChatResponse:
    """将处理后的领域数据模型转换成接口数据模型"""
    return ChatResponse(
        message_id=processed_result.message_id,
        messages=[
            ChatBotMessage(
                text=bot_message.text,
                object=ChatObject(
                    id=bot_message.object.id,
                    type=bot_message.object.type,
                    title=bot_message.object.title,
                    attributes=bot_message.object.attributes
                ) if bot_message.object is not None else None
            )
            for bot_message in (processed_result.messages or [])
        ]
    )

@router.get("/api/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history_endpoint(sender_id, service: DialogueStateServiceDep):

    chat_history_messages = await service.get_chat_history(sender_id)

    return ChatHistoryResponse(sender_id=sender_id,messages=chat_history_messages)