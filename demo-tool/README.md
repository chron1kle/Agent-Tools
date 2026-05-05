# {{TOOL_NAME}}

> 一句话描述工具功能

## 功能特性

- 特性 1
- 特性 2
- 特性 3

## 快速开始

```bash
# 生命周期管理
python -m {{TOOL_NAME}}.src --start    # 启动工具进程
python -m {{TOOL_NAME}}.src --status   # 查询状态
python -m {{TOOL_NAME}}.src --stop     # 停止工具进程
python -m {{TOOL_NAME}}.src --restart  # 重启工具进程

# MCP 模式（强烈推荐 - 生产环境使用）
python -m {{TOOL_NAME}}.src --mcp
```

> **强烈推荐**：生产环境只使用 MCP 模式调用工具。单例模式确保工具进程持续运行，Claude 可精确控制生命周期。

## 目录结构

```
{{TOOL_NAME}}/
├── src/                    # 源代码
│   ├── __init__.py         # 统一入口（MCP + 普通模式）
│   ├── main.py             # Python 实现
│   ├── index.js            # Node.js 实现（可选）
│   └── main.go             # Go 实现（可选）
├── config.json             # 配置文件
├── README.md               # 本文件
└── manual.md               # 详细手册（可选）
```

## 配置

详见 `config.json` 和 `manual.md`。

## 文档

- [详细手册](./manual.md)
- [Agent Tools 规范](../../AGENT_TOOL_STANDARD.md)
