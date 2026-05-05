# Agent Tools Workflow Engine

> 工作流引擎 - 统一的任务编排与执行系统

## 概述

工作流引擎是一个底层基础设施，用于：
- 编排多步骤任务
- 管理工具生命周期
- 处理错误和重试
- 追踪执行状态

## 核心概念

### 工作流 (Workflow)

```
输入 → [步骤1] → [步骤2] → [步骤3] → 输出
           ↓           ↓
         并行       依赖
```

### 步骤 (Step)

- **工具**: 执行什么
- **依赖**: 需要先完成哪些步骤
- **映射**: 如何传递数据
- **错误策略**: 失败时怎么办

## 快速开始

```python
from engine import WorkflowEngine, Workflow, Step

# 创建工作流
workflow = Workflow(
    id="my-workflow",
    name="我的工作流",
    steps=[
        Step(id="step1", name="步骤1", tool="tool-a", depends_on=[]),
        Step(id="step2", name="步骤2", tool="tool-b", depends_on=["step1"])
    ]
)

# 执行
engine = WorkflowEngine()
result = await engine.run(workflow, inputs={"key": "value"})
```

## 目录结构

```
engine/
├── src/
│   ├── __init__.py       # 主入口
│   ├── workflow.py       # 工作流模型
│   ├── step.py          # 步骤模型
│   ├── adapter.py       # 工具适配器
│   ├── registry.py      # 工具注册表
│   ├── executor.py      # 执行引擎
│   ├── lifecycle.py    # 生命周期管理
│   ├── state.py        # 状态存储
│   └── events.py       # 事件系统
├── workflows/            # 工作流定义
│   └── pdf-to-book.json
├── config.json
└── README.md
```

## 核心组件

| 组件 | 职责 |
|------|------|
| WorkflowExecutor | DAG 构建与执行 |
| LifecycleManager | 实例管理与状态追踪 |
| ToolRegistry | 工具注册与发现 |
| EventBus | 事件发布与订阅 |

## 配置

```json
{
  "engine": {
    "max_concurrent_workflows": 10,
    "default_timeout": 3600
  }
}
```

## 错误处理策略

| 策略 | 说明 |
|------|------|
| RETRY | 重试 N 次 |
| SKIP | 跳过步骤 |
| ABORT | 终止工作流 |
| COMPENSATE | 执行补偿 |

---

**版本**: 1.0.0
**最后更新**: 2026-05-05
