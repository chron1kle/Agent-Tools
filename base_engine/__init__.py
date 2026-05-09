"""Base Engine - Lego workflow engine common components

包含：队列、任务、日志、LLM、配置等基础组件。
引擎组件（TaskQueue, Scheduler 等）在 base_engine.engine 子模块中。
"""

from _queue.base_queue import BaseQueue
from task import Task, TaskFactory, TaskIDGenerator, CallFrame, ErrorInfo
from _logging import logger, LogPoller, _log_queue
from llm import (
    ModelRegistry, model_registry,
    LLMClient, LLMResponse, CallOptions, llm_client,
    ContextAssembler, context_assembler,
    ResponseValidator, response_validator,
)
from config import ConfigRegistry, config_registry
from .engine import TaskQueue, task_queue, Scheduler, scheduler
from .engine import JudgmentManual, TransitionDecider, TransitionResult

__all__ = [
    # queue
    "BaseQueue",
    # task
    "Task", "TaskFactory", "TaskIDGenerator", "CallFrame", "ErrorInfo",
    # logging
    "logger", "LogPoller", "_log_queue",
    # llm
    "ModelRegistry", "model_registry",
    "LLMClient", "LLMResponse", "CallOptions", "llm_client",
    "ContextAssembler", "context_assembler",
    "ResponseValidator", "response_validator",
    # config
    "ConfigRegistry", "config_registry",
    # engine (子模块)
    "TaskQueue", "task_queue", "Scheduler", "scheduler",
    "JudgmentManual", "TransitionDecider", "TransitionResult",
]
