# Agent Tools Workflow Engine - 解决方案

> **版本**: 1.0
> **创建日期**: 2026-05-05

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Workflow Engine                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  Registry   │  │  Executor    │  │  Lifecycle      │    │
│  │  (工具注册)  │  │  (执行引擎)   │  │  Manager        │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │  State       │  │  Event        │  │  Error          │    │
│  │  Store       │  │  Bus         │  │  Handler        │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Tool Adapters                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  pdf2epub   │  │  tool-a      │  │  tool-b      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、目录结构

```
engine/
├── src/
│   ├── __init__.py
│   ├── workflow.py          # 工作流定义与模型
│   ├── step.py              # 步骤定义
│   ├── executor.py          # 执行引擎
│   ├── registry.py          # 工具注册表
│   ├── lifecycle.py        # 生命周期管理
│   ├── state.py            # 状态存储
│   ├── events.py           # 事件系统
│   ├── error.py            # 错误处理
│   └── adapter.py          # 工具适配器基类
├── workflows/               # 工作流定义
│   └── pdf2epub-workflow.json
├── config.json
└── README.md
```

---

## 三、核心模型

### 3.1 工作流 (Workflow)

```python
@dataclass
class Workflow:
    id: str
    name: str
    description: str
    version: str
    inputs: List[Input]
    outputs: List[Output]
    steps: List[Step]
    config: WorkflowConfig
```

### 3.2 步骤 (Step)

```python
@dataclass
class Step:
    id: str
    name: str
    tool: str                    # 工具名称
    input_mapping: Dict[str, str]  # 输入映射
    output_mapping: Dict[str, str] # 输出映射
    depends_on: List[str]        # 依赖步骤
    condition: Optional[str]      # 执行条件
    error_strategy: ErrorStrategy  # 错误策略
    retry: RetryConfig           # 重试配置
```

### 3.3 工具适配器 (ToolAdapter)

```python
class ToolAdapter(ABC):
    name: str
    version: str

    @abstractmethod
    async def execute(self, inputs: Dict) -> Dict:
        """执行工具，返回输出"""
        pass

    @abstractmethod
    async def validate_inputs(self, inputs: Dict) -> bool:
        """验证输入"""
        pass

    async def get_status(self) -> ToolStatus:
        """获取状态"""
        pass

    async def start(self):
        """启动工具"""
        pass

    async def stop(self):
        """停止工具"""
        pass
```

---

## 四、执行流程

### 4.1 DAG 构建

```
1. 解析工作流定义
2. 构建依赖图
3. 拓扑排序
4. 确定执行计划
```

### 4.2 执行流程

```
开始
  │
  ▼
┌─────────────────┐
│  构建执行计划   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  选择可执行步骤 │ ←── 依赖已满足
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  执行步骤       │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 成功？   │
    └────┬────┘
   Yes   │   No
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌────────────┐
│ 更新  │ │ 错误处理   │
│ 状态  │ └─────┬──────┘
└───┬───┘       │
    │    ┌─────┴─────┐
    │    │Retry/Skip  │
    │    │/Abort      │
    │    └─────┬─────┘
    │          │
    └────┬────┘
         ▼
    所有步骤完成？
         │
    Yes  │  No
    ┌────┴────┐
    ▼         ▼
  完成     返回选择
```

---

## 五、错误处理策略

### 5.1 策略类型

```python
class ErrorStrategy(Enum):
    RETRY = "retry"           # 重试
    SKIP = "skip"             # 跳过
    FALLBACK = "fallback"     # 备用方案
    ABORT = "abort"           # 终止
    COMPENSATE = "compensate" # 补偿
```

### 5.2 重试配置

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
```

---

## 六、工具注册

### 6.1 注册方式

```python
# 方式1: 代码注册
registry.register("pdf2epub", PDF2EPUBAdapter)

# 方式2: 配置注册
# workflows/pdf2epub.json
{
  "tools": [
    {
      "name": "pdf2epub",
      "adapter": "pdf2epub.PDF2EPUBAdapter",
      "config": {...}
    }
  ]
}
```

### 6.2 适配器示例

```python
class PDF2EPUBAdapter(ToolAdapter):
    name = "pdf2epub"
    version = "1.0"

    async def execute(self, inputs: Dict) -> Dict:
        # 调用现有工具
        result = subprocess.run([
            "python", "-m", "pdf2epub.src",
            inputs["input"],
            "--output", inputs.get("output", "out")
        ])
        return {"output": result.stdout}

    async def validate_inputs(self, inputs: Dict) -> bool:
        return "input" in inputs and Path(inputs["input"]).exists()
```

---

## 七、MCP 接口

### 7.1 工具列表

```python
@app.list_tools()
async def list_tools():
    return [
        Tool(name="execute_workflow", ...),
        Tool(name="get_workflow_status", ...),
        Tool(name="list_workflows", ...),
        Tool(name="register_tool", ...),
    ]
```

### 7.2 执行工作流

```python
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "execute_workflow":
        workflow_id = arguments["workflow_id"]
        result = await executor.run(workflow_id, arguments.get("inputs"))
        return [TextContent(type="text", json.dumps(result))]
```

---

## 八、配置

### 8.1 config.json

```json
{
  "engine": {
    "max_concurrent_steps": 3,
    "default_timeout": 3600,
    "state_store": "memory"
  },
  "workflows_dir": "./workflows",
  "tools_dir": "./tools"
}
```

### 8.2 环境变量

| 变量 | 说明 |
|------|------|
| ENGINE_MAX_CONCURRENT | 最大并发步骤数 |
| ENGINE_TIMEOUT | 默认超时时间 |
| ENGINE_STATE_STORE | 状态存储方式 |

---

## 九、使用示例

### 9.1 创建工作流

```json
// workflows/pdf-to-book.json
{
  "id": "pdf-to-book",
  "name": "PDF 转电子书",
  "steps": [
    {
      "id": "extract",
      "tool": "pdf2epub",
      "input_mapping": {
        "input": "$.inputs.file"
      },
      "error_strategy": "retry"
    },
    {
      "id": "validate",
      "tool": "validator",
      "depends_on": ["extract"],
      "input_mapping": {
        "file": "$.steps.extract.outputs.epub"
      }
    }
  ]
}
```

### 9.2 执行工作流

```python
from engine import WorkflowEngine

engine = WorkflowEngine()
result = await engine.run("pdf-to-book", inputs={"file": "book.pdf"})
```

---

## 十、与现有架构的集成

### 10.1 复用现有组件

- `common/task-queue` → 任务队列
- `common/logger` → 日志系统
- `common/conf-env-reg` → 配置管理

### 10.2 渐进式迁移

1. **第一阶段**: 仅作为执行层，上层仍是单工具调用
2. **第二阶段**: 工作流编排，但单步执行
3. **第三阶段**: 完整 DAG 并行执行

---

**最后更新**: 2026-05-05
