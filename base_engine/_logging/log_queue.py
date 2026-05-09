"""Log queue - 日志写入队列"""

import threading
from _queue.base_queue import BaseQueue


class LogQueue(BaseQueue):
    """日志队列"""

    def __init__(self):
        super().__init__()

    def _handle(self, item):
        """执行写入（item 是可调用对象）"""
        item()


# 模块级单例
_log_queue = LogQueue()
