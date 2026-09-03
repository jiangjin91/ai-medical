"""
边数据模型
顺序边
条件边
默认兜底边
"""
from dataclasses import dataclass


@dataclass(slots=True)
class FlowStepLink:
    """
    三种边的基类
    """
    target: str     # 下一个节点的节点ID


@dataclass(slots=True)
class FlowStepStaticLink(FlowStepLink):
    pass


@dataclass(slots=True)
class FlowStepConditionLink(FlowStepLink):
    condition: str


@dataclass(slots=True)
class FlowStepFallbackLink(FlowStepLink):
    pass