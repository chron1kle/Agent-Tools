"""Log poller - 实时日志轮询器，增量读取新日志"""

import os
import json
from typing import Dict, List, Optional


class LogPoller:
    """实时日志轮询器"""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self._positions: Dict[str, int] = {}  # task_id -> file_position

    def _get_path(self, task_id: str) -> str:
        return os.path.join(self.log_dir, f"{task_id}.log")

    def read_new(self, task_id: str) -> List[dict]:
        """读取新日志（增量读取）

        Returns:
            新增的日志条目列表
        """
        log_path = self._get_path(task_id)
        if not os.path.exists(log_path):
            return []

        position = self._positions.get(task_id, 0)

        with open(log_path, "r", encoding="utf-8") as f:
            f.seek(position)

            new_entries = []
            for line in f:
                line = line.strip()
                if line:
                    try:
                        new_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            self._positions[task_id] = f.tell()

        return new_entries

    def read_all(self, task_id: str) -> List[dict]:
        """读取全部日志"""
        log_path = self._get_path(task_id)
        if not os.path.exists(log_path):
            return []

        with open(log_path, "r", encoding="utf-8") as f:
            entries = []
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return entries

    def reset(self, task_id: str):
        """重置读取位置（下一次 read_new 从头读）"""
        self._positions.pop(task_id, None)
