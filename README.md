# Agent Tools

> AI Agent 工具项目的标准化架构与参考实现

---

## 项目愿景

建立一套标准化的 Agent Tools 开发框架，实现统一入口、单例模式、多语言支持。

## 核心文档

| 文档 | 定位 | 说明 |
|------|------|------|
| [AGENT_TOOL_STANDARD.md](./AGENT_TOOL_STANDARD.md) | 项目架构 | 整体架构设计、核心决策 |
| [demo-tool/](./demo-tool/) | 工具模板 | 工具实现模板、使用指南 |
| [maintenance.md](./maintenance.md) | 维护手册 | 文档维护规范 |

---

## 快速开始

### 创建新工具

```bash
# 1. 复制模板
cp -r demo-tool/ my-tool/

# 2. 重命名并编辑占位符
cd my-tool
# 编辑 src/__init__.py，替换 {{TOOL_NAME}}

# 3. 实现工具逻辑
# 编辑 src/main.py

# 4. 启动工具
python -m my_tool.src --mcp
```

---

## 架构概览

```
Claude Desktop ──MCP──> __init__.py (单例) ──> Tool 实现
```

| 特性 | 说明 |
|------|------|
| 统一入口 | 所有工具通过 `src/__init__.py` 调用 |
| 单例模式 | Claude 控制工具生命周期 |
| MCP 主要接口 | 生产环境使用 MCP 模式 |

---

## 目录结构

```
Agent-Tools/
├── AGENT_TOOL_STANDARD.md  # 项目架构文档
├── README.md               # 本文件
├── maintenance.md          # 维护手册
├── demo-tool/            # 工具模板
├── pdf2epub/             # 参考实现
└── common/               # 公共组件
    ├── logger/
    └── conf-env-reg/
```

---

## 组件状态

| 组件 | 状态 |
|------|------|
| conf-env-reg (Python) | ✅ 可用 |
| Logger (Python) | ✅ 可用 |
| Logger (Node.js) | ⏳ 待实现 |
| Logger (Go) | ⏳ 待实现 |

---

**最后更新**: 2026-05-05
