from typing import Any

from atguigu.task.action.base import Action


class ActionRegister:

    def __init__(self):
        self.actions: dict[str, Any] = {}

    def register_action(self, action: Action):
        self.actions[action.name] = action

    def get_action(self,action_name: str) -> Action:
        return self.actions[action_name]