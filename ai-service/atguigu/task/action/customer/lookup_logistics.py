from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import fetch_logistics


class ActionLookupLogisticsStatus(Action):
    name = "action_lookup_logistics"

    async def run(self, action_kwargs: dict[str, Any], dialogue_state: DialogueState) -> ActionResult:
        # 1.获取请求参数
        order_number = dialogue_state.active_task.slots.get("order_number")

        # 2. 给中台服务发送获取订单物流的请求
        payload = await fetch_logistics(order_number)

        # 3. 封装到ActionResult的slots中返回
        if payload is None:
            return ActionResult(
                updated_slots={
                    "tracking_number": "未知",
                    "logistics_company": "未知",
                    "logistics_status": "暂时无法查到物流信息，请稍后再试。",
                }
            )

        return ActionResult(updated_slots={
            "tracking_number": payload.get("tracking_number") or "未知",
            "logistics_company": payload.get("logistics_company") or "未知",
            "logistics_status": payload.get("status_desc") or payload.get("status") or "未知",
        })