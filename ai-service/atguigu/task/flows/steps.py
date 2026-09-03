"""
定义步骤
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atguigu.task.flows.links import FlowStepLink, FlowStepStaticLink, FlowStepConditionLink, FlowStepFallbackLink


class FlowStepType(Enum):
    """枚举"""
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"

@dataclass(slots=True)
class ResponseDefinition:
    text: str
    mode: str = "static"   # static generate(llm生成) rephrase(llm改写)
    prompt: str | None = None


@dataclass(slots=True)
class Validated:
    condition: str
    failure_response: ResponseDefinition | None = None

@dataclass(slots=True)
class FlowStep:
    """流程步骤"""

    id: str                                                     #   步骤id
    type: FlowStepType                                          #   枚举
    next: list[FlowStepLink]       # 步骤的边（列表，可能是多个条件）

    @staticmethod
    def from_dict(step_data: dict[str, Any]) -> "FlowStep":
        type = step_data["type"]
        clz = FLOW_STEP_TO_CLASS[type]
        return clz.from_dict(step_data)


    @staticmethod
    def load_base_fields(step_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": step_data["id"],
            "type": FlowStepType(step_data["type"]),
            "next": FlowStep.load_step_next(step_data["next"])
        }


    @staticmethod
    def load_step_next(links: str | list[dict[str, Any]]) -> list[FlowStepLink]:
        loaded_links: list[FlowStepLink] = []
        if isinstance(links, str):
            loaded_links.append(FlowStepStaticLink(links))
        else:
            for link_dict in links:
                if "if" in link_dict:
                    loaded_links.append(FlowStepConditionLink(condition=link_dict["if"],target=link_dict["then"]))
                else:
                    loaded_links.append(FlowStepFallbackLink(target=link_dict["else"]))

        return loaded_links

@dataclass(slots=True)
class StartFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_dict: dict[str, Any]) -> "StartFlowStep":
        return cls(
            **FlowStep.load_base_fields(step_dict)
        )

@dataclass(slots=True)
class EndFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_dict: dict[str, Any]) -> "EndFlowStep":
        return cls(
            **FlowStep.load_base_fields(step_dict)
        )

# 继承FlowStep
@dataclass(slots=True)
class ActionFlowStep(FlowStep):
    action: str                                             # 行动的名字
    args: dict[str, Any] = field(default_factory=dict)      # 行动的参数

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(
            **FlowStep.load_base_fields(step_data),
            action=step_data["action"],
            args=step_data.get("args",{})
        )

@dataclass(slots=True)
class CollectFlowStep(FlowStep):
    slot_name: str
    response: ResponseDefinition  # 数据模型对象
    validated: Validated | None = None  # 插件思想


    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectFlowStep":
        return cls(
            **FlowStep.load_base_fields(step_data),
            slot_name = step_data["slot_name"],
            response = ResponseDefinition(
                text=step_data["response"]["text"],
                mode=step_data["response"].get("mode","static"),
                prompt=step_data["response"].get("prompt")
            ),
            validated = Validated(
                condition=step_data["validated"]["condition"],
                failure_response=ResponseDefinition(
                    text=step_data["validated"]["failure_response"]["text"],
                    mode=step_data["validated"]["failure_response"].get("mode","static"),
                    prompt=step_data["validated"]["failure_response"].get("prompt")
                ) if step_data["validated"].get("failure_response") is not None else None
            ) if step_data.get("validated") is not None else None
        )

FLOW_STEP_TO_CLASS: dict[str, type[FlowStep]] = {
    "start": StartFlowStep,
    "end": EndFlowStep,
    "action": ActionFlowStep,
    "collect": CollectFlowStep
}