"""Base queue system - 所有队列的基类"""

import queue
import threading
from typing import Callable, Any


class BaseQueue:
    """队列基类"""

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        """启动队列消费线程（子类可覆写以禁用）"""
        self._running = True
        self._thread = threading.Thread(target=self._consume, daemon=True)
        self._thread.start()

    def stop(self):
        """停止队列"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)

    def put(self, item: Any):
        """加入队列"""
        self._q.put(item)

    def _consume(self):
        """消费队列（子类可覆写）"""
        while self._running:
            try:
                item = self._q.get(timeout=0.1)
                self._handle(item)
            except queue.Empty:
                continue

    def _handle(self, item: Any):
        """处理队列项（子类实现）"""
        raise NotImplementedError
