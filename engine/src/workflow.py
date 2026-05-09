"""
Workflow Definition - 工作流定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ErrorStrategy(Enum):
    """错误处理策略"""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ABORT = "abort"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0


@dataclass
class Step:
    """工作流步骤定义

    一个步骤对应一个工具（tool_id），步骤之间的依赖通过 depends_on 定义。
    步骤执行时会创建一个 Task，Task 的状态流转由该工具的 JudgmentManual 定义。
    """
    id: str                           # 步骤 ID
    name: str                         # 步骤名称
    tool_id: str                      # 工具 ID（对应 JudgmentManual）
    input_mapping: Dict[str, str] = field(default_factory=dict)   # 输入映射
    output_mapping: Dict[str, str] = field(default_factory=dict)  # 输出映射
    depends_on: List[str] = field(default_factory=list)          # 依赖步骤
    condition: Optional[str] = None                               # 执行条件
    error_strategy: ErrorStrategy = ErrorStrategy.RETRY           # 错误策略
    retry: RetryConfig = field(default_factory=RetryConfig)       # 重试配置


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str
    version: str = "1.0"
    inputs: List[Any] = field(default_factory=list)   # 简化：只需定义
    outputs: List[Any] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> Optional[Step]:
        """获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self, completed_steps: set) -> List[Step]:
        """获取所有依赖已满足的就绪步骤"""
        ready = []
        for step in self.steps:
            if step.id in completed_steps:
                continue
            if all(dep in completed_steps for dep in step.depends_on):
                ready.append(step)
        return ready

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "tool_id": s.tool_id,
                    "depends_on": s.depends_on,
                    "error_strategy": s.error_strategy.value,
                }
                for s in self.steps
            ]
        }
