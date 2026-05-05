"""
Task Queue 配置管理
支持从 config.json 或环境变量读取配置
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskQueueConfig:
    """任务队列配置"""
    max_workers: int = 3  # 最大并发数
    progress_interval: float = 1.0  # 进度报告间隔（秒）
    task_timeout: int = 3600  # 任务超时时间（秒）
    queue_max_size: int = 100  # 队列最大大小


def get_queue_config(
    prefix: str = "TASKQUEUE",
    config: Optional[dict] = None
) -> TaskQueueConfig:
    """
    获取任务队列配置

    优先级：环境变量 > config > 默认值

    Args:
        prefix: 环境变量前缀
        config: 额外的配置字典

    Returns:
        TaskQueueConfig: 配置对象
    """
    # 默认值
    max_workers = 3
    progress_interval = 1.0
    task_timeout = 3600
    queue_max_size = 100

    # 从环境变量读取
    env_max_workers = os.environ.get(f"{prefix}_MAX_WORKERS")
    if env_max_workers:
        max_workers = int(env_max_workers)

    env_progress_interval = os.environ.get(f"{prefix}_PROGRESS_INTERVAL")
    if env_progress_interval:
        progress_interval = float(env_progress_interval)

    env_task_timeout = os.environ.get(f"{prefix}_TASK_TIMEOUT")
    if env_task_timeout:
        task_timeout = int(env_task_timeout)

    env_queue_max_size = os.environ.get(f"{prefix}_QUEUE_MAX_SIZE")
    if env_queue_max_size:
        queue_max_size = int(env_queue_max_size)

    # 从 config 字典覆盖（优先级最高）
    if config:
        task_config = config.get("task_queue", {})
        if "max_workers" in task_config:
            max_workers = task_config["max_workers"]
        if "progress_interval" in task_config:
            progress_interval = task_config["progress_interval"]
        if "task_timeout" in task_config:
            task_timeout = task_config["task_timeout"]
        if "queue_max_size" in task_config:
            queue_max_size = task_config["queue_max_size"]

    return TaskQueueConfig(
        max_workers=max_workers,
        progress_interval=progress_interval,
        task_timeout=task_timeout,
        queue_max_size=queue_max_size
    )
