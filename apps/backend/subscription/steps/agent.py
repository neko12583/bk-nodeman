# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import abc
from typing import List, Optional, Tuple, Union

from django.conf import settings
from django.utils.translation import ugettext as _

from apps.backend import constants as backend_const
from apps.backend.agent.manager import AgentManager
from apps.node_man import constants, models
from apps.node_man.models import GsePluginDesc, SubscriptionStep
from pipeline import builder
from pipeline.builder.flow.base import Element

# 需分发到 PROXY 的文件（由于放到一次任务中会给用户等待过久的体验，因此拆分成多次任务）
from .base import Action, Step


class AgentStep(Step):
    # 订阅步骤类型
    STEP_TYPE = constants.SubStepType.AGENT

    # 需要自动拉起的插件列表
    auto_launch_plugins: Optional[List[models.GsePluginDesc]] = None

    def __init__(self, subscription_step: SubscriptionStep):
        self.auto_launch_plugins = GsePluginDesc.get_auto_launch_plugins()
        super(AgentStep, self).__init__(subscription_step)

    def get_package_by_os(self, os_type):
        return

    def get_supported_actions(self):
        supported_actions = [
            InstallAgent,
            ReinstallAgent,
            UninstallAgent,
            UpgradeAgent,
            RestartAgent,
            InstallProxy,
            ReinstallProxy,
            UninstallProxy,
            ReplaceProxy,
            UpgradeProxy,
            RestartProxy,
            ReloadAgent,
            ReloadProxy,
        ]
        return {action.ACTION_NAME: action for action in supported_actions}

    def get_step_data(self, instance_info, target_host, agent_config):
        """
        获取步骤上下文数据
        """
        return

    def generate_agent_control_info(self, host_status):
        """
        生成Agent控制信息
        """
        return

    def make_instances_migrate_actions(self, instances, auto_trigger=False, preview_only=False, **kwargs):
        """
        安装Agent不需要监听CMDB变更
        若有需要按CMDB拓扑变更自动安装Agent的需求，需完善此方法
        """
        instance_actions = {instance_id: self.subscription_step.config["job_type"] for instance_id in instances}
        return {"instance_actions": instance_actions, "migrate_reasons": {}}

    def bulk_create_host_status_cache(self, *args, **kwargs):
        """
        todo 此函数作占位用防止重试功能报错暂无具体功能
        :return:
        """
        pass


class AgentAction(Action, abc.ABC):
    """
    步骤动作调度器
    """

    ACTION_NAME = ""
    # 动作描述
    ACTION_DESCRIPTION = ""

    def __init__(self, action_name, step: AgentStep, instance_record_ids: List[int]):
        """
        :param Step step: 步骤实例
        :param models.SubscriptionInstanceRecord instance_record_ids: 订阅实例执行记录
        """
        self.step = step
        super().__init__(action_name, step, instance_record_ids)

    def get_agent_manager(self, subscription_instances: List[models.SubscriptionInstanceRecord]):
        """
        根据主机生成Agent管理器
        """
        subscription_instance_ids = [sub_inst.id for sub_inst in subscription_instances]
        return AgentManager(subscription_instance_ids, self.step)

    @abc.abstractmethod
    def _generate_activities(self, agent_manager):
        pass

    def inject_vars_to_global_data(self, global_pipeline_data: builder.Data):
        global_pipeline_data.inputs["${blueking_language}"] = builder.Var(
            type=builder.Var.PLAIN, value=self.step.subscription_step.params.get("blueking_language")
        )
        super().inject_vars_to_global_data(global_pipeline_data)

    def generate_activities(
        self,
        subscription_instances: List[models.SubscriptionInstanceRecord],
        global_pipeline_data: builder.Data,
        current_activities=None,
    ) -> Tuple[List[Union[builder.ServiceActivity, Element]], Optional[builder.Data]]:
        agent_manager = self.get_agent_manager(subscription_instances)
        self.inject_vars_to_global_data(global_pipeline_data)
        return self._generate_activities(agent_manager)

    def append_delegate_activities(self, agent_manager, activities):
        for plugin in self.step.auto_launch_plugins:
            activities.append(agent_manager.delegate_plugin(plugin.name))
        return activities

    @staticmethod
    def append_push_file_activities(agent_manager, activities):
        for file in constants.FILES_TO_PUSH_TO_PROXY:
            activities.append(agent_manager.push_files_to_proxy(file))
        return activities


class InstallAgent(AgentAction):
    """
    安装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_AGENT
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.register_host(),
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.install_plugins(),
        ]

        return list(filter(None, activities)), None


class ReinstallAgent(AgentAction):
    """
    重装Agent
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_AGENT
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
            agent_manager.install_plugins(),
        ]

        return list(filter(None, activities)), None


class UpgradeAgent(ReinstallAgent):
    """
    升级Agent
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_AGENT
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.run_upgrade_command(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]
        return activities, None


class RestartAgent(AgentAction):
    """
    重启Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_AGENT
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]

        return activities, None


class RestartProxy(AgentAction):
    """
    重启Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RESTART_PROXY
    ACTION_DESCRIPTION = "重启"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.restart(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
        ]
        return activities, None


class InstallProxy(AgentAction):
    """
    安装Proxy，与安装Agent流程一致
    """

    ACTION_NAME = backend_const.ActionNameType.INSTALL_PROXY
    ACTION_DESCRIPTION = "安装"

    def _generate_activities(self, agent_manager: AgentManager):
        register_host = agent_manager.register_host()
        activities = [
            register_host,
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
        ]

        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())
        activities.append(agent_manager.install_plugins())

        return list(filter(None, activities)), None


class ReinstallProxy(AgentAction):
    """
    重装Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REINSTALL_PROXY
    ACTION_DESCRIPTION = "重装"

    def _generate_activities(self, agent_manager: AgentManager):

        activities = [
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.configure_policy(),
            agent_manager.choose_ap(),
            agent_manager.install(),
            # 重装时由于初始 Proxy 的状态仍是RUNNING，这里等待30秒再重新查询
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING, name=_("查询Proxy状态")),
        ]

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())
        activities.append(agent_manager.install_plugins())

        return list(filter(None, activities)), None


class UpgradeProxy(ReinstallProxy):
    """
    升级Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UPGRADE_PROXY
    ACTION_DESCRIPTION = "升级"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.push_upgrade_package(),
            agent_manager.run_upgrade_command(),
            agent_manager.wait(30),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]

        # 推送文件到proxy
        activities = self.append_push_file_activities(agent_manager, activities)
        activities.append(agent_manager.start_nginx())

        return activities, None


class ReplaceProxy(InstallProxy):
    """
    替换Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.REPLACE_PROXY
    ACTION_DESCRIPTION = "替换"


class UninstallAgent(AgentAction):
    """
    卸载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_AGENT
    ACTION_DESCRIPTION = "卸载"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.query_tjj_password() if settings.USE_TJJ else None,
            agent_manager.uninstall_agent(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.UNKNOWN),
            agent_manager.update_process_status(status=constants.ProcStateType.NOT_INSTALLED),
        ]

        return list(filter(None, activities)), None


class UninstallProxy(AgentAction):
    """
    卸载Proxy
    """

    ACTION_NAME = backend_const.ActionNameType.UNINSTALL_PROXY
    ACTION_DESCRIPTION = "卸载"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.uninstall_proxy(),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.UNKNOWN, name=_("查询Proxy状态")),
            agent_manager.update_process_status(status=constants.ProcStateType.NOT_INSTALLED),
        ]

        return activities, None


class ReloadAgent(AgentAction):
    """
    重载Agent
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_AGENT
    ACTION_DESCRIPTION = "重载配置"

    def _generate_activities(self, agent_manager: AgentManager):
        activities = [
            agent_manager.check_agent_status(),
            agent_manager.update_install_info(),
            agent_manager.render_and_push_gse_config(),
            agent_manager.reload_agent(skip_polling_result=True),
            agent_manager.wait(5),
            agent_manager.get_agent_status(expect_status=constants.ProcStateType.RUNNING),
        ]
        return activities, None


class ReloadProxy(ReloadAgent):
    """
    重载proxy
    """

    ACTION_NAME = backend_const.ActionNameType.RELOAD_PROXY
    ACTION_DESCRIPTION = "重载配置"
