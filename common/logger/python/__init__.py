"""
Agent Logger - Python 实现
基于 TCP Socket 的日志组件，支持多客户端广播

使用方式：
    from common.logger.python import Logger

    logger = Logger({"port": 8765, "level": "INFO"})
    logger.info("extract_start", {"file": "test.pdf"})
"""

from .logger import SocketLogger
from .logger import get_logger
from .logger import create_logger_decorator

__all__ = ["Logger", "get_logger", "create_logger_decorator"]

# 导出主类
Logger = SocketLogger
