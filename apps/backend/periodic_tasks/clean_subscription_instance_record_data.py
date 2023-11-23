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
from typing import Dict, Union, List

from celery.schedules import crontab
from celery.task import periodic_task
from django.db import connection
from django.utils import timezone

from apps.backend import constants
from common.log import logger
from apps.node_man import models
from apps.utils.time_handler import strftime_local


@periodic_task(
    queue="default",
    options={"queue": "default"},
    run_every=crontab(minute="*/5"),
)
def clean_subscription_instance_record_data():
    # 清理数据开关以及相关配置
    clean_subscription_data_map: Dict[str, Union[int, str, bool]] = (
        models.GlobalSettings.get_config(models.GlobalSettings.KeyEnum.CLEAN_SUBSCRIPTION_DATA_MAP.value) or {}
    )
    enable_clean_subscription_data: bool = clean_subscription_data_map.get("enable_clean_subscription_data", True)
    if not enable_clean_subscription_data:
        logger.info("clean_subscription_data is not enable, delete subscription data will be skipped")
        return

    limit: int = clean_subscription_data_map.get("limit", constants.DEFAULT_CLEAN_RECORD_LIMIT)
    alive_days: int = clean_subscription_data_map.get("alive_days", constants.DEFAULT_ALIVE_TIME)

    logger.info(
        f"periodic_task -> clean_subscription_instance_record_data, "
        f"start to clean subscription instance record and pipeline tree data,"
        f" alive_days: {alive_days}, limit: {limit}"
    )

    with connection.cursor() as cursor:
        # 获取策略类型任务
        select_policy_subscription_sql: str = f"SELECT id FROM node_man_subscription " \
            f"WHERE category = '{models.Subscription.CategoryType.POLICY}';"
        cursor.execute(select_policy_subscription_sql)
        policy_subscription_ids: List[int] = [row[0] for row in cursor.fetchall()]

        # 获取需要清理的 instance_record_ids
        if policy_subscription_ids:
            select_clean_records_sql: str = f"SELECT id, task_id FROM node_man_subscriptioninstancerecord " \
                f"WHERE NOT({generate_query_scope('subscription_id', policy_subscription_ids)}) " \
                f"AND create_time < DATE_SUB(NOW(), INTERVAL {alive_days} DAY) AND is_latest = 0  LIMIT {limit};"
        else:
            select_clean_records_sql: str = f"SELECT id, task_id FROM node_man_subscriptioninstancerecord " \
                f"WHERE create_time < DATE_SUB(NOW(), INTERVAL {alive_days} DAY) AND is_latest = 0  LIMIT {limit};"
        cursor.execute(select_clean_records_sql)
        clean_records: tuple[tuple[int, int]] = cursor.fetchall()

        if not clean_records:
            logger.info(
                "need_clean_instance_records_ids is empty, "
                "delete subscription instance record data will be skipped"
            )
            return

        need_clean_instance_record_ids: List[int] = list()
        need_clean_task_ids: List[int] = list()
        for clean_record in clean_records:
            need_clean_instance_record_ids.append(clean_record[0])
            need_clean_task_ids.append(clean_record[1])

        # 获取需要清理的 pipeline_tree_ids
        select_pipeline_ids_sql: str = f"SELECT pipeline_id from node_man_subscriptiontask " \
            f"WHERE {generate_query_scope('id', need_clean_task_ids)};"
        cursor.execute(select_pipeline_ids_sql)
        need_clean_pipeline_tree_ids: List[str] = [row[0] for row in cursor.fetchall()]

        # 清理数据
        delete_subscription_instance_record_sql: str = f"DELETE FROM node_man_subscriptioninstancerecord " \
            f"WHERE {generate_query_scope('id', need_clean_instance_record_ids)};"
        log_sql(delete_subscription_instance_record_sql)
        cursor.execute(delete_subscription_instance_record_sql)

        delete_subscription_task_sql: str = f"DELETE FROM node_man_subscriptiontask " \
            f"WHERE {generate_query_scope('id', need_clean_task_ids)};"
        log_sql(delete_subscription_task_sql)
        cursor.execute(delete_subscription_task_sql)

        if need_clean_pipeline_tree_ids:
            delete_pipeline_tree_sql: str = f"DELETE FROM node_man_pipelinetree " \
                f"WHERE {generate_query_scope('id', need_clean_pipeline_tree_ids)};"
            log_sql(delete_pipeline_tree_sql)
            cursor.execute(delete_pipeline_tree_sql)


def log_sql(execute_sql: str):
    logger.info(
        f"periodic_task -> clean_subscription_instance_record_data, time -> {strftime_local(timezone.now())}, "
        f"start to execute sql -> [{execute_sql}]"
    )


def generate_query_scope(fields_name: str, scopes: list) -> str:
    if not scopes:
        return ""

    if len(scopes) == 1:
        return f"{fields_name}='{scopes[0]}'"

    return f"{fields_name} in {tuple(scopes)}"
