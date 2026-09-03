from dataclasses import dataclass, field

from atguigu.task.flows.steps import FlowStep

@dataclass(slots=True)
class FlowSlot:
    slot_name: str
    type: str
    label: str
    description: str

@dataclass(slots=True)
class Flow:
    """不区分系统流程和业务流程"""
    flow_id: str            # 流程id
    flow_name: str          # 流程名称
    description: str        # 描述
    steps: list[FlowStep]     #流程步骤
    slots: dict[str, FlowSlot] = field(default_factory=dict)

    def get_step_by_id(self, step_id: str) -> FlowStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

@dataclass(slots=True)
class FlowList:
    """承载yaml文件中的顶层元素（slots：user_flows.yml中/flows:两份yml文件都有）"""
    flows: list[Flow]
    slots: dict[str, FlowSlot] = field(default_factory=dict)        # key是字典的名字

    def get_flow_by_id(self, flow_id) -> Flow | None:
        for flow in self.flows:
            if flow.flow_id == flow_id:
                return flow

        return None

