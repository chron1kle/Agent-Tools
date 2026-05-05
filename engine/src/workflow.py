"""
Workflow Engine - 工作流定义与模型
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ErrorStrategy(Enum):
    """错误处理策略"""
    RETRY = "retry"
    SKIP = "skip"
    FALLBACK = "fallback"
    ABORT = "abort"
    COMPENSATE = "compensate"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Input:
    """工作流输入定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Output:
    """工作流输出定义"""
    name: str
    type: str
    description: str


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0


@dataclass
class Step:
    """工作流步骤定义"""
    id: str
    name: str
    tool: str
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    error_strategy: ErrorStrategy = ErrorStrategy.RETRY
    retry: RetryConfig = field(default_factory=RetryConfig)


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str
    version: str = "1.0"
    inputs: List[Input] = field(default_factory=list)
    outputs: List[Output] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "inputs": [i.__dict__ for i in self.inputs],
            "outputs": [o.__dict__ for o in self.outputs],
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "tool": s.tool,
                    "depends_on": s.depends_on,
                    "error_strategy": s.error_strategy.value
                }
                for s in self.steps
            ]
        }


@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_states: Dict[str, StepStatus] = field(default_factory=dict)
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "step_states": {k: v.value for k, v in self.step_states.items()},
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }
