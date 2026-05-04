# Agent Tools

> AI Agent 工具项目的标准化架构与参考实现

---

## 项目目标

建立一套标准化的 Agent Tools 开发规范，让不同语言、不同功能的 AI 工具能够：

1. **统一结构** - 遵循相同的目录组织和配置文件格式
2. **LLM 集成** - 支持通过 MCP 协议被 LLM 直接调用
3. **可观测** - 通过统一的日志系统实时追踪工具运行状态
4. **跨语言** - 提供各语言的通用组件（Python 优先）

---

## 核心规范

| 文档 | 说明 |
|------|------|
| [AGENT_TOOL_STANDARD.md](./AGENT_TOOL_STANDARD.md) | Agent Tool 构建规范（必读） |
| [common/logger/README.md](./common/logger/README.md) | 日志系统架构设计 |

---

## 目录结构

```
Agent-Tools/
├── AGENT_TOOL_STANDARD.md    # 架构规范文档
├── .gitignore                # Git 忽略配置
├── README.md                 # 本文件
├── pdf2epub/                 # 参考实现（PDF 转 EPUB）
│   ├── config.json
│   ├── src/
│   └── manual.md
└── common/                   # 通用组件
    └── logger/              # 日志组件
        └── python/          # Python 实现
```

---

## 快速开始

### 1. 创建新工具

按照 [AGENT_TOOL_STANDARD.md](./AGENT_TOOL_STANDARD.md) 创建目录结构：

```
my-tool/
├── config.json
├── README.md
├── .gitignore
└── src/
    └── __init__.py
```

### 2. 可选：集成日志

```python
from common.logger.python import Logger

logger = Logger({"port": 8765})
logger.info("task_start", {"file": "input.pdf"})
```

监听日志：
```bash
telnet localhost 8765
```

### 3. 可选：集成 MCP

实现 `src/mcp_server.py`，让工具可以被 LLM 直接调用。

---

## 参考实现

| 工具 | 说明 |
|------|------|
| [pdf2epub](./pdf2epub/) | PDF 转 EPUB，支持 OCR 纠错和 LLM 校正 |

---

## 组件状态

| 组件 | 语言 | 状态 |
|------|------|------|
| Logger | Python | ✅ 可用 |
| Logger | Node.js | ⏳ 待实现 |
| Logger | Go | ⏳ 待实现 |
| Logger | Rust | ⏳ 待实现 |

---

**最后更新**: 2026-05-05
