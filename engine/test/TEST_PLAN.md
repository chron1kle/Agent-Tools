# Engine Test Plan

> **日期**: 2026-05-07
> **目标**: 设计 engine 的测试策略和用例

---

## 一、测试目标

验证 engine 的核心功能：
1. 工作流定义与解析
2. 工具注册与发现
3. 工作流执行（DAG 拓扑排序）
4. 错误处理（重试、跳过、终止）
5. 事件发布与订阅
6. 状态追踪

---

## 二、测试策略

### 2.1 测试层次

| 层次 | 范围 | 测试方式 |
|------|------|---------|
| **单元测试** | 独立的类/函数 | pytest + mock |
| **集成测试** | 多组件协作 | pytest + 真实组件 |
| **端到端测试** | 完整工作流执行 | pytest + 真实引擎 |

### 2.2 测试框架选择

- **pytest**: Python 事实标准，支持 asyncio
- **pytest-asyncio**: 支持异步测试
- **pytest-mock**: 模拟外部依赖

### 2.3 测试数据管理

- 使用 `conftest.py` 管理 fixtures
- 工作流定义使用 JSON 或代码中的 dataclass

---

## 三、测试用例设计

### 3.1 单元测试

**Workflow 模型测试**
| 用例 | 输入 | 预期输出 |
|------|------|---------|
| 创建工作流 | 有效的 steps | workflow.id 正确 |
| 获取就绪步骤 | 空的已完成集合 | 根步骤就绪 |
| 获取就绪步骤 | 根步骤完成 | 依赖步骤就绪 |
| 依赖环检测 | 循环依赖 | 抛出异常或返回错误 |

**ToolRegistry 测试**
| 用例 | 输入 | 预期输出 |
|------|------|---------|
| 注册工具 | adapter | 成功注册 |
| 获取工具 | 存在的名称 | 返回 adapter |
| 获取工具 | 不存在的名称 | 返回 None |
| 列出工具 | 已注册多个 | 返回全部 |

**TransitionDecider 测试**
| 用例 | 输入 | 预期输出 |
|------|------|---------|
| 正常流转 | idle + start | pending |
| 错误流转 | executing + error | failed |
| 重试策略 | NetworkError | 保持当前状态 |
| 跳过策略 | * + skip | 下一状态 |

### 3.2 集成测试

**WorkflowEngine 集成测试**
| 用例 | 描述 |
|------|------|
| 单步骤工作流 | 提交 → 执行 → 完成 |
| 多步骤串行工作流 | 步骤按依赖顺序执行 |
| 多步骤并行工作流 | 无依赖步骤并行执行 |
| 错误处理工作流 | 失败后按策略处理 |

**EventBus 集成测试**
| 用例 | 描述 |
|------|------|
| 事件发布/订阅 | 发布后订阅者收到 |
| 事件历史 | 可查询历史事件 |
| 异步订阅 | 异步 callback 正常执行 |

### 3.3 端到端测试

| 用例 | 描述 |
|------|------|
| 完整工作流执行 | 从创建到完成的完整生命周期 |

---

## 四、测试目录结构

```
engine/
├── test/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_workflow.py     # Workflow 模型测试
│   │   ├── test_registry.py     # ToolRegistry 测试
│   │   └── test_decider.py      # TransitionDecider 测试
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_engine.py       # 引擎集成测试
│   │   └── test_event_bus.py    # 事件总线测试
│   └── e2e/
│       ├── __init__.py
│       └── test_complete_flow.py # 端到端测试
├── requirements-test.txt          # 测试依赖
└── pytest.ini                    # pytest 配置
```

---

## 五、实施计划

1. **Phase 1**: 搭建测试基础设施
   - 创建 pytest.ini
   - 创建 conftest.py
   - 创建 requirements-test.txt

2. **Phase 2**: 单元测试
   - test_workflow.py
   - test_registry.py
   - test_decider.py

3. **Phase 3**: 集成测试
   - test_engine.py
   - test_event_bus.py

4. **Phase 4**: 端到端测试
   - test_complete_flow.py

---

## 六、Mock 策略

对于外部依赖：
- **LLMClient**: Mock 掉，不真实调用 API
- **ToolAdapter**: 使用 MockToolAdapter
- **文件系统**: 使用 tmp_path fixture

---

## 七、预期产出

- 完整的测试套件
- 可执行的测试命令
- 测试覆盖率报告（可选）
