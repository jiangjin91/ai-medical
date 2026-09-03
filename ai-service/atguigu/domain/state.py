"""

主要管理某一个用户（sender_id）的完整对话状态：四类
1. 任务相关信息【TaskContext/SystemContext】:
2. 会话相关的信息
3. 轮次相关的信息
4. 用户点击卡片信息【FocusedObject】

8月15号 不要管谁掉。
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from atguigu.domain.contexts import TaskContext, SystemContext
from atguigu.domain.messages import UserMessage, BotMessage, FocusedObject

@dataclass(slots=True)
class Turn:
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_message": self.user_message.to_dict(),
            "bot_messages": [BotMessage.to_dict(bot_message) for bot_message in self.bot_messages]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id = data["turn_id"],
            user_message = UserMessage.from_dict(data["user_message"]),
            bot_messages = [BotMessage.from_dict(bot_message) for bot_message in data["bot_messages"]] if data["bot_messages"] is not None else None,
        )

@dataclass(slots=True)
class Session:
    session_id: str
    started_at: float  # session的创建时间（未使用）
    activated_at: float  # session的激活时间：判断session是否过期了，如果过期了，创建一个新的session，如果没有过期继续复用Session，更新activated_at即可
    closed_at: float | None = None  # session的关闭时间 （未使用）
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "activated_at": self.activated_at,
            "closed_at": self.closed_at,
            "turns": [turn.to_dict() for turn in (self.turns or [])]
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id = data["session_id"],
            started_at = data["started_at"],
            activated_at = data["activated_at"],
            closed_at = data["closed_at"],
            turns = [Turn.from_dict(turn) for turn in (data["turns"] or [])]
        )

@dataclass(slots=True)
class DialogueState:
    """
    超大的仓库：
    给这个大仓库放东西【分阶段来放】
    从这个大仓库拿东西【后续引擎操作时候需要的数据都从DialogueState获取】
    """

    sender_id: str
    active_task: TaskContext | None = None  # 当前【正在执行】激活的业务流程任务
    paused_tasks: list[TaskContext] = field(default_factory=list)  # 被挂起的业务流程任务
    active_system_task: SystemContext | None = None # 当前【正在执行】激活的系统流程任务
    sessions: list[Session] = field(default_factory=list) # 会话信息多次
    current_session_id: str | None = None # 当前的session会话ID 方便获取到当前创建的session对象
    focused_object: FocusedObject | None = None # 卡片信息
    pending_turn: Turn | None = None # 缓冲区

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "active_task": TaskContext.to_dict(self.active_task) if self.active_task is not None else None,
            "paused_tasks": [TaskContext.to_dict(paused_task) for paused_task in self.paused_tasks],
            "active_system_task": self.active_system_task.to_dict() if self.active_system_task is not None else None,
            "sessions": [session.to_dict() for session in self.sessions],
            "current_session_id": self.current_session_id,
            "focused_object": self.focused_object.to_dict() if self.focused_object is not None else None,
            "pending_turn": self.pending_turn.to_dict() if self.pending_turn is not None else None
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueState":
        return cls(
            sender_id = data["sender_id"],
            active_task = TaskContext.from_dict(data["active_task"]) if data["active_task"] is not None else None,
            paused_tasks = [TaskContext.from_dict(paused_task) for paused_task in data["paused_tasks"]],
            active_system_task = SystemContext.from_dict(data["active_system_task"]) if data["active_system_task"] is not None else None,
            sessions = [Session.from_dict(session) for session in data["sessions"]],
            current_session_id = data["current_session_id"],
            focused_object = FocusedObject.from_dict(data["focused_object"]) if data["focused_object"] is not None else None,
            pending_turn = Turn.from_dict(data["pending_turn"]) if data["pending_turn"] is not None else None
        )

    ################################################任务相关方法########################################################

    def start_task(self, task_context: TaskContext):
        """启动任务流程"""
        self.active_task = task_context

    def end_active_task(self):
        """结束当前任务"""
        self.active_task = None

    def cancel_active_task(self):
        """取消当前执行的业务流程任务以及系统流程任务"""
        # todo 需要将挂起的任务从paused_tasks中移除吗
        self.active_task = None
        self.active_system_task = None

    def remove_paused_tasks(self, flow_id: str):
        """移除暂停栈中的业务流程任务"""
        self.paused_tasks = [paused_task for paused_task in self.paused_tasks if paused_task.flow_id != flow_id]

    def interrupt_active_task(self):
        """中断当前执行业务流程任务"""
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resume_task(self, flow_id: str | None = None):
        """恢复挂起的业务流程任务"""
        # 暂停栈中没有元素
        if not self.paused_tasks:
            return False

        if flow_id is None:
            paused_task = self.paused_tasks.pop()
            self.active_task = paused_task
            return True

        for paused_task in self.paused_tasks:
            if paused_task.flow_id == flow_id:
                self.active_task = paused_task
                self.paused_tasks.remove(paused_task)
                return True

        return False

    def start_system_task(self, system_context: SystemContext):
        self.active_system_task = system_context

    def end_system_task(self):
        self.active_system_task = None

    def current_task(self):
        """返回**当前真正要驱动对话的上下文**,系统任务优先"""
        return self.active_system_task or self.active_task

    ################################################槽位相关########################################################

    def set_slots(self, slots: dict[str, Any]):
        """批量写槽位"""
        if self.active_task is not None:
            self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str):
        """删除槽位"""
        if self.active_task is not None:
            self.active_task.slots.pop(slot_name)

    ################################################会话与轮次相关########################################################

    def start_session(self):
        """开启一个新会话"""
        now = time.time()
        session = Session(
            session_id= str(uuid.uuid4()),
            started_at= now,
            activated_at= now
        )
        self.sessions.append(session)
        self.current_session_id= session.session_id

    def current_session(self) -> Session | None:
        """获取当前会话对象"""
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session
        return None

    def close_current_session(self):
        """关闭当前会话"""
        if self.current_session():
            self.current_session().closed_at = time.time()

        self.current_session_id = None

    def reset_runtime_state_for_new_session(self):
        """
        职责： 当前的session超时，会把超时的这个session之前的对话状态清空（判断session超时的规则...）
        Returns:
        """
        # 任务相关的
        self.active_task = None
        self.active_system_task = None
        self.paused_tasks = []

        # 卡片相关的
        self.focused_object = None

        # 暂存区
        self.pending_turn = None

    ################################################轮次相关方法########################################################

    def begin_turn(self, user_message: UserMessage):
        """
        职责：实例化turn对象
        Args:
            user_message:

        Returns:

        """
        # 实例化turn对象
        turn = Turn(
            turn_id=str(uuid.uuid4().hex),
            user_message=user_message,
            bot_messages=[]
        )

        # 将turn对象赋值到缓冲区
        self.pending_turn = turn

    def commit_pending_turn(self):
        """
        职责：将缓存区的内容更新到当前的session中 并且清空缓冲区
        Returns:

        """
        # 将缓存区的内容更新到当前的session中
        if self.current_session():
            self.current_session().turns.append(self.pending_turn)

        # 清空缓冲区
        self.pending_turn = None

    ################################################对象相关方法########################################################
    def set_focused_object(self, object: FocusedObject):
        """
        职责：将点击的卡片对象的信息更新到focused_object
        Args:
            object:

        Returns:

        """
        self.focused_object = object





