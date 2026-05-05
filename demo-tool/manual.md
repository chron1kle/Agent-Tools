# {{TOOL_NAME}} 详细手册

## 一、工具概述

详细描述工具的功能、用途和使用场景。

## 二、目录结构

```
{{TOOL_NAME}}/
├── src/                    # 源代码
│   ├── __init__.py         # 统一入口
│   ├── main.py             # Python 实现
│   ├── index.js            # Node.js 实现（可选）
│   └── main.go             # Go 实现（可选）
├── config.json             # 配置文件
├── README.md              # 简要介绍
└── manual.md              # 本文件
```

## 三、配置文件说明

### config.json

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| version | string | "1.0" | 版本号 |
| description | string | - | 工具描述 |
| log.enabled | boolean | true | 是否启用日志 |
| log.port | number | 8765 | 日志端口 |
| log.level | string | "INFO" | 日志级别 |
| output.default_dir | string | "out" | 默认输出目录 |
| mcp.enabled | boolean | false | 是否启用 MCP |

## 四、使用方法

> **强烈推荐**：生产环境只使用 MCP 模式调用工具。单例模式确保工具进程持续运行，Claude 可精确控制生命周期。

### 4.1 生命周期管理

```bash
# 启动工具进程
python -m {{TOOL_NAME}}.src --start

# 查询状态
python -m {{TOOL_NAME}}.src --status

# 停止工具进程
python -m {{TOOL_NAME}}.src --stop

# 重启工具进程
python -m {{TOOL_NAME}}.src --restart
```

### 4.2 MCP 模式

```bash
# 启动 MCP 服务器
python -m {{TOOL_NAME}}.src --mcp
```

MCP 模式启动后，LLM 可以通过 MCP 协议调用此工具。

### 4.3 编程调用

```python
from {{TOOL_NAME}}.src import run

# 运行工具
result = run("--input", "input.pdf")
```

## 五、处理流程

```
输入文件
    │
    ▼
┌─────────────────┐
│  步骤1: 读取   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  步骤2: 处理   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  步骤3: 输出   │
└─────────────────┘
    │
    ▼
输出文件
```

## 六、常见问题

### Q1: 问题1

A1: 答案1

### Q2: 问题2

A2: 答案2

## 七、输出文件说明

| 文件 | 说明 |
|------|------|
| output/file1 | 输出文件1 |
| output/file2 | 输出文件2 |

## 八、依赖列表

根据使用的语言安装相应依赖：

**Python**：
```
pip install requests
```

**Node.js**：
```
npm install
```

**Go**：
```
go mod init
go mod tidy
```

---

**最后更新**: {{DATE}}
