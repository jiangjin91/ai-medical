from dataclasses import field, dataclass
from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import ActionResult
from atguigu.task.action.register import ActionRegister

"""
负责：从注册中心根据action的名字找具体的Action对象，在执行找到Action对象的run方法
"""

@dataclass(slots=True)
class ActionCall:
    action_name: str
    action_kwargs: dict[str, Any] = field(default_factory=dict)


class ActionRunner:

    def __init__(self, action_register: ActionRegister):
        self.action_register = action_register


    async def run(self, action_call: ActionCall, dialogue_state: DialogueState) -> ActionResult:

        action = self.action_register.get_action(action_call.action_name)

        action_result =await action.run(action_call.action_kwargs, dialogue_state)

        return action_result