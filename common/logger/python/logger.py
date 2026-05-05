import socket
import threading
import json
import os
from datetime import datetime
from enum import IntEnum
from typing import Optional


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


def _load_config_from_env() -> dict:
    """从环境变量加载日志配置"""
    config = {}
    config["enabled"] = os.environ.get("AGENT_LOGGER_ENABLED", "true").lower() == "true"
    config["host"] = os.environ.get("AGENT_LOGGER_HOST", "localhost")
    config["port"] = int(os.environ.get("AGENT_LOGGER_PORT", "8765"))
    config["level"] = os.environ.get("AGENT_LOGGER_LEVEL", "INFO")
    return config


class SocketLogger:
    """基于 TCP Socket 的日志组件，支持多客户端广播"""

    def __init__(self, config: Optional[dict] = None):
        # 优先使用传入的 config，其次使用环境变量
        if config is None:
            config = _load_config_from_env()
        else:
            # 如果传入了 config，仍然可以覆盖环境变量设置
            env_config = _load_config_from_env()
            config = {**env_config, **config}  # 环境变量作为默认值，传入参数覆盖

        self.enabled = config.get("enabled", True)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 8765)
        self.level = LogLevel[config.get("level", "INFO").upper()]

        self._server_socket: Optional[socket.socket] = None
        self._clients: list = []
        self._running = False

        if self.enabled:
            self._start_server()

    def _start_server(self):
        """启动 TCP Server"""
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._running = True

            thread = threading.Thread(target=self._accept_clients, daemon=True)
            thread.start()
        except OSError as e:
            print(f"[Logger] Failed to start server on {self.host}:{self.port}: {e}")
            self.enabled = False

    def _accept_clients(self):
        """接受客户端连接"""
        while self._running:
            try:
                client, addr = self._server_socket.accept()
                self._clients.append(client)
            except OSError:
                break

    def _broadcast(self, record: dict):
        """广播日志到所有客户端"""
        if not self.enabled:
            return

        msg = json.dumps(record, ensure_ascii=False) + "\n"
        msg_bytes = msg.encode("utf-8")

        for client in self._clients[:]:
            try:
                client.send(msg_bytes)
            except OSError:
                self._clients.remove(client)

    def _log(self, level: LogLevel, event: str, data: Optional[dict] = None):
        """输出日志"""
        if level < self.level:
            return

        record = {
            "timestamp": datetime.now().isoformat(),
            "level": level.name,
            "event": event,
            "message": event.replace("_", " "),
            "data": data or {}
        }
        self._broadcast(record)

    def debug(self, event: str, data: Optional[dict] = None):
        """调试信息"""
        self._log(LogLevel.DEBUG, event, data)

    def info(self, event: str, data: Optional[dict] = None):
        """普通信息"""
        self._log(LogLevel.INFO, event, data)

    def warning(self, event: str, data: Optional[dict] = None):
        """警告"""
        self._log(LogLevel.WARNING, event, data)

    def error(self, event: str, data: Optional[dict] = None):
        """错误"""
        self._log(LogLevel.ERROR, event, data)

    def close(self):
        """关闭连接"""
        self._running = False
        for client in self._clients:
            try:
                client.close()
            except OSError:
                pass
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass


# ============ 兼容旧 API ============

def get_logger(config: Optional[dict] = None) -> SocketLogger:
    """获取 Logger 实例的便捷函数"""
    return SocketLogger(config)


# ============ 装饰器方式（可选） ============

def create_logger_decorator(default_config: dict):
    """创建 Logger 装饰器"""
    def decorator(cls):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            log_config = default_config.copy()
            self._logger = SocketLogger(log_config)

        cls.__init__ = new_init
        cls.log = property(lambda self: self._logger)

        return cls

    return decorator


# 便捷装饰器（默认配置）
def Logger(config: Optional[dict] = None):
    """Logger 装饰器，默认配置"""
    return create_logger_decorator(config or {"port": 8765})


# 导出主类
Logger = SocketLogger
