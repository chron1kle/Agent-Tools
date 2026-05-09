"""Task logger - 按任务 ID 写独立日志文件"""

import os
import json
from .log_queue import _log_queue


class TaskLogger:
    """日志写入器"""

    def __init__(self):
        self._queue = _log_queue

    def _write(self, item):
        """执行写入"""
        log_path, entry = item
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            if not os.path.exists(log_path):
                open(log_path, "w", encoding="utf-8").close()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def enqueue(self, log_dir: str, task_id: str, event: str, timestamp: int, **kwargs):
        """入队

        Args:
            log_dir: 日志目录
            task_id: 任务 ID（作为文件名）
            event: 事件类型
            timestamp: 毫秒级时间戳
            **kwargs: 其他字段
        """
        log_path = os.path.join(log_dir, f"{task_id}.log")
        entry = {"timestamp": timestamp, "event": event, **kwargs}
        self._queue.put((log_path, entry))


# 模块级单例
logger = TaskLogger()
