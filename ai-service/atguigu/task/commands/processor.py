from atguigu.domain.contexts import SystemTaskCanceledContext, TaskContext, SystemTaskInterruptedContext, \
    SystemTaskStartedContext, SystemTaskResumedContext, SystemTaskResumeFailedContext
from atguigu.domain.state import DialogueState
from atguigu.task.commands.command import Command, StartFlowCommand, SetSlotsCommand, ResumedFlowCommand, \
    CancelFlowCommand
from atguigu.task.flows.flows import FlowList


class CommandProcessor:

    def process_command(self, commands: list[Command], dialogue_state: DialogueState, flow_list: FlowList):
        """
        分别处理四种具体的命令
        Returns:
        """

        # 循环处理
        for command in commands:
            if isinstance(command,StartFlowCommand):
                self._start_flow(command, dialogue_state, flow_list)
            if isinstance(command,SetSlotsCommand):
                self._update_slots(command, dialogue_state)
            if isinstance(command,ResumedFlowCommand):
                self._resumed_flow(command, dialogue_state, flow_list)
            if isinstance(command,CancelFlowCommand):
                self._cancel_flow(dialogue_state, flow_list)

    def _update_slots(self, command: Command, dialogue_state: DialogueState):
        """
        给业务流程缺失的槽位信息补全信息
        Args:
            command:
            dialogue_state:

        Returns:

        """
        dialogue_state.set_slots(command.slots)

    def _cancel_flow(self, dialogue_state: DialogueState, flow_list: FlowList):
        """
        取消当前业务流程，更新业务流程上下文和更新系统流程上下午
        Args:
            dialogue_state:
            flow_list:

        Returns:

        """
        # 获取当前业务流程
        activate_task = dialogue_state.active_task

        # 当前没有正在执行的业务流程，不需要取消
        if activate_task is None:
            return

        # 取消当前业务流程以及系统流程
        dialogue_state.cancel_active_task()

        # 激活取消系统流程(让用户看到取消系统流程的开场白)
        dialogue_state.start_system_task(
            system_context=SystemTaskCanceledContext(
                flow_id = "system_task_canceled",
                step_id = "start",
                canceled_flow_id = activate_task.flow_id,
                canceled_flow_name = flow_list.get_flow_by_id(activate_task.flow_id).flow_name
            )
        )

    def _start_flow(self, command: Command, dialogue_state: DialogueState, flow_list: FlowList):
        """
        开启业务流程，更新业务流程上下文和系统流程上下文
        Args:
            command:
            dialogue_state:
            flow_list:

        Returns:

        """
        # 当前业务流程是否存在，移除paused_task, 更新系统上下文流程，更细系统流程上下文
        active_task = dialogue_state.active_task

        # 目标业务流程
        start_flow_id = command.flow

        if active_task is not None:
            # 业务流程一致，不做处理
            if start_flow_id == active_task.flow_id:
                return 
            
            # 移除paused_task中的flow
            dialogue_state.remove_paused_tasks(start_flow_id)

            # 中断正在执行的业务流程
            dialogue_state.interrupt_active_task()

            # 更新当前业务流程
            dialogue_state.start_task(
                TaskContext(flow_id=start_flow_id,step_id="start")
            )

            # 更新系统流程
            dialogue_state.start_system_task(
                SystemTaskInterruptedContext(
                    flow_id = "system_task_interrupted",
                    step_id = "start",
                    interrupted_flow_id = active_task.flow_id,
                    interrupted_flow_name = flow_list.get_flow_by_id(active_task.flow_id).flow_name,
                    started_flow_id = start_flow_id,
                    started_flow_name = flow_list.get_flow_by_id(start_flow_id).flow_name
                )
            )
        else:
            # 当前没有开启的业务流程
            # 移除paused_task中的业务流程
            dialogue_state.remove_paused_tasks(start_flow_id)

            # 更新业务流程
            dialogue_state.start_task(
                TaskContext(flow_id=start_flow_id, step_id="start")
            )

            # 更新系统流程
            dialogue_state.start_system_task(
                SystemTaskStartedContext(
                    flow_id = "system_task_started",
                    step_id = "start",
                    started_flow_id = start_flow_id,
                    started_flow_name = flow_list.get_flow_by_id(start_flow_id).flow_name
                )
            )

    def _resumed_flow(self, command: Command, dialogue_state: DialogueState, flow_list: FlowList):
        """
        恢复业务流程，更新业务流程和系统流程
        Args:
            command:
            dialogue_state:
            flow_list:

        Returns:

        """
        # 要恢复的业务流程
        resumed_flow_id = command.flow

        # 当前运行的业务流程
        active_task = dialogue_state.active_task

        if active_task is not None:

            # 未指定目标流程时，继续当前正在运行的流程
            if resumed_flow_id is None:
                return

            # 如果目标恢复流程和当前运行流程一致就不管
            if active_task.flow_id == resumed_flow_id:
                return

            # 中断当前运行业务流程
            dialogue_state.interrupt_active_task()

            # 从挂起业务流程上下文的栈中恢复
            resumed = dialogue_state.resume_task(resumed_flow_id)

            # 如果恢复不成功
            if not resumed:
                # 回滚 把刚刚压入到栈中的当前执行的业务流程上下文恢复出来
                dialogue_state.resume_task()

                # 激活恢复失败的系统流程
                dialogue_state.start_system_task(
                    SystemTaskResumeFailedContext(
                        flow_id = "system_task_resume_failed",
                        step_id = "start"
                    )
                )

            # 恢复业务流程成功,激活中断系统流程
            else:
                dialogue_state.start_system_task(
                    SystemTaskInterruptedContext(
                        flow_id="system_task_interrupted",
                        step_id="start",
                        interrupted_flow_id = active_task.flow_id,
                        interrupted_flow_name = flow_list.get_flow_by_id(active_task.flow_id).flow_name,
                        started_flow_id = dialogue_state.active_task.flow_id,
                        started_flow_name = flow_list.get_flow_by_id(dialogue_state.active_task.flow_id).flow_name
                    )
                )
        else:
            # 指定流程时按ID恢复；未指定时恢复暂停栈顶的流程
            resumed = dialogue_state.resume_task(resumed_flow_id)

            if not resumed:
                # 激活业务流程
                dialogue_state.start_system_task(SystemTaskResumeFailedContext(
                    flow_id = "system_task_resume_failed",
                    step_id = "start"
                ))
            else:
                # 激活恢复成功系统流程
                dialogue_state.start_system_task(
                    SystemTaskResumedContext(
                        flow_id="system_task_resumed",
                        step_id="start",
                        resumed_flow_id=dialogue_state.active_task.flow_id,
                        resumed_flow_name=flow_list.get_flow_by_id(dialogue_state.active_task.flow_id).flow_name
                    )
                )







            
