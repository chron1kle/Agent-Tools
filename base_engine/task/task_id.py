"""Task ID generator - 毫秒级时间戳 + 碰撞处理"""

import time
import threading
from typing import Dict


class TaskIDGenerator:
    """任务 ID 生成器"""

    _lock = threading.Lock()
    _registry: Dict[int, int] = {}  # timestamp -> collision_count

    @classmethod
    def generate(cls) -> str:
        """生成唯一任务 ID

        正常情况返回毫秒级时间戳字符串，如 "1746512367000"
        碰撞时返回带后缀的字符串，如 "1746512367000-1"
        """
        with cls._lock:
            timestamp = int(time.time() * 1000)

            if timestamp in cls._registry:
                cls._registry[timestamp] += 1
                return f"{timestamp}-{cls._registry[timestamp]}"
            else:
                cls._registry[timestamp] = 0
                return str(timestamp)

    @classmethod
    def register(cls, task_id: str) -> None:
        """手动注册任务 ID（用于恢复场景）

        解析 task_id 并更新 registry，确保后续生成不会碰撞
        """
        with cls._lock:
            parts = task_id.split("-")
            timestamp = int(parts[0])

            if len(parts) > 1:
                suffix = int(parts[1])
                cls._registry[timestamp] = max(cls._registry.get(timestamp, 0), suffix)
            else:
                cls._registry[timestamp] = max(cls._registry.get(timestamp, 0), 0)
