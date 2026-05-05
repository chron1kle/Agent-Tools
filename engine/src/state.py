"""
State Store - 状态存储
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path


class StateStore:
    """
    状态存储

    支持内存和文件两种模式。
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._memory: Dict[str, Any] = {}

        # 如果有存储路径，加载已有状态
        if storage_path and Path(storage_path).exists():
            self._load()

    def _load(self):
        """从文件加载"""
        try:
            with open(self.storage_path, 'r') as f:
                self._memory = json.load(f)
        except Exception:
            self._memory = {}

    def _save(self):
        """保存到文件"""
        if self.storage_path:
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self._memory, f, indent=2)

    def set(self, key: str, value: Any):
        """设置值"""
        self._memory[key] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        return self._memory.get(key, default)

    def delete(self, key: str):
        """删除值"""
        if key in self._memory:
            del self._memory[key]
            self._save()

    def keys(self):
        """获取所有键"""
        return self._memory.keys()

    def clear(self):
        """清空"""
        self._memory = {}
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """获取所有数据"""
        return self._memory.copy()
