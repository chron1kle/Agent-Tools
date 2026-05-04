# Agent Tool 构建规范

> **版本**: 1.2
> **适用场景**: AI Agent 工具类项目的标准化结构

---

## 一、目录结构

```
project-name/
├── config.json          # 配置文件（可选）
├── README.md            # 简要介绍（必选）
├── manual.md            # 详细手册（可选，复杂工具必选）
├── .gitignore         # Git忽略配置（必选）
└── src/               # 源代码目录（必选）
    ├── __init__.py    # 包初始化文件（Python 项目必选，其他语言可省）
    ├── mcp_server.py  # MCP Server（可选，需要 LLM 接口时）
    └── *.py           # 功能模块
```

## 二、文件规范

### 2.1 config.json

可选文件。如果工具需要外部配置：

```json
{
  "version": "1.0",
  "description": "项目描述",
  "output": {
    "default_dir": "out"
  }
}
```

### 2.2 README.md

简短介绍，包含：
- 一句话功能描述
- 特性列表
- 快速开始示例
- 文档链接

### 2.3 manual.md

详细手册，包含：
- 工具概述
- 目录结构
- 配置文件说明
- 使用方法
- 命令行参数
- 处理流程
- 常见问题
- 输出文件说明
- 依赖列表

### 2.4 .gitignore

标准项目忽略配置：
- `__pycache__/`（Python）
- `*.py[cod]`
- `node_modules/`（Node.js）
- `target/`（Rust）
- `venv/`, `env/`
- `.idea/`, `.vscode/`
- `.env`, `*.log`

### 2.5 src/__init__.py

包初始化文件，至少包含项目名称注释。**仅 Python 项目需要**。

## 三、LLM 集成（可选扩展）

> **说明**：LLM 能力是**扩展选项**，不是必需项。纯自动化、数据处理、文件转换等工具不需要此配置。

如果工具需要调用 LLM：

### 3.1 config.json 扩展

```json
{
  "llm": {
    "provider": "anthropic|openai|ollama|自定义",
    "api_key": "",
    "base_url": "",
    "model": "",
    "max_tokens": 8192
  }
}
```

### 3.2 API 配置获取示例

```python
def get_api_config(config: dict = None) -> dict:
    """从配置中获取 API 相关配置"""
    if config is None:
        config = load_config()

    llm_config = config.get("llm", {})
    api_key = llm_config.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    return {
        "api_key": api_key,
        "model": llm_config.get("model", "default-model"),
        "base_url": llm_config.get("base_url", ""),
        "max_tokens": llm_config.get("max_tokens", 8192)
    }
```

### 3.3 配置优先级

CLI 参数 > config.json > 环境变量 > 默认值

## 四、MCP 接口（可选扩展）

> **说明**：MCP (Model Context Protocol) 是让 LLM 直接调用工具的标准协议。实现 MCP 后，工具可在 Claude Desktop 等支持 MCP 的客户端中直接使用。

### 4.1 MCP Server 实现要求

工具需实现 MCP Server，实现以下能力：

| 能力 | 说明 |
|------|------|
| `tools/list` | 返回可用工具列表（含 input_schema） |
| `tools/call` | 执行工具调用 |

### 4.1.1 config.json 声明

在 `config.json` 中声明 MCP 支持：

```json
{
  "mcp": {
    "enabled": true,
    "command": "python",
    "args": ["-m", "src.mcp_server"]
  }
}
```

字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `enabled` | 是 | 是否启用 MCP |
| `command` | 是 | 启动命令（如 `python`、`node`、`go run`） |
| `args` | 是 | 命令参数数组 |
| `cwd` | 否 | 工作目录 |

> **注意**：此配置是工具的**自述性声明**，告诉用户和 MCP 客户端如何启动这个工具。实际客户端配置（如 Claude Desktop 的 `settings.json`）需要用户手动添加。

### 4.2 Tool Schema 定义

每个工具需提供 JSON Schema：

```json
{
  "name": "extract_pdf_text",
  "description": "从 PDF 文件中提取文本内容",
  "input_schema": {
    "type": "object",
    "properties": {
      "pdf_path": {
        "type": "string",
        "description": "PDF 文件的完整路径"
      },
      "start_page": {
        "type": "integer",
        "description": "起始页码（从1开始）",
        "default": 1
      },
      "end_page": {
        "type": "integer",
        "description": "结束页码（包含）"
      }
    },
    "required": ["pdf_path"]
  }
}
```

### 4.3 config.json 扩展

```json
{
  "mcp": {
    "enabled": true,
    "command": "python",
    "args": ["-m", "src.mcp_server"]
  }
}
```

### 4.4 MCP Server 示例

```python
# src/mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import json

app = Server("pdf2epub")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="extract_pdf_text",
            description="从 PDF 文件中提取文本内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "PDF 文件路径"
                    }
                },
                "required": ["pdf_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "extract_pdf_text":
        # 执行逻辑
        return [TextContent(type="text", text=json.dumps(result))]
    raise ValueError(f"Unknown tool: {name}")
```

### 4.5 Claude Desktop 配置

```json
{
  "mcpServers": {
    "pdf2epub": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/project"
    }
  }
}
```

## 五、日志系统（可选扩展）

> **说明**：日志系统用于实时输出工具运行状态，方便调试和追溯。采用 TCP Socket 广播模式，语言无关。

### 5.1 设计思路

- **配置外部化** - 端口等配置从 config.json 读取
- **TCP 广播** - 多客户端可同时监听
- **组件化解耦** - 使用各语言的 logger 组件（见 `common/logger/`）

### 5.1.1 日志 API 使用方式

每个工具通过调用日志组件输出日志，API 设计如下：

```python
# 方式1: 初始化并使用（推荐）
from agent_logger import Logger

logger = Logger(config={"port": 8765, "level": "INFO"})

# 输出日志
logger.info("extract_start", {"pdf_path": "/path/to/file.pdf"})
logger.info("extract_progress", {"current": 10, "total": 100})
logger.error("extract_failed", {"error": "file not found"})

# 方式2: 通过装饰器自动初始化
@Logger(config={"port": 8765})
class PDFTool:
    def extract(self, path):
        self.log.info("start", {"path": path})  # self.log 自动可用
```

日志 API 统一接口：

| 方法 | 参数 | 说明 |
|------|------|------|
| `debug(event, data)` | 事件名, 数据字典 | 调试信息 |
| `info(event, data)` | 事件名, 数据字典 | 普通信息 |
| `warning(event, data)` | 事件名, 数据字典 | 警告 |
| `error(event, data)` | 事件名, 数据字典 | 错误 |

其中 `data` 为可选字典，可包含任意调试信息。

### 5.2 config.json 扩展

```json
{
  "log": {
    "enabled": true,
    "host": "localhost",
    "port": 8765,
    "level": "INFO"
  }
}
```

### 5.3 日志格式

```json
{
  "timestamp": "2026-05-05T00:18:00",
  "level": "INFO",
  "event": "extract_start",
  "message": "开始提取PDF",
  "data": {
    "path": "/path/to/file.pdf"
  }
}
```

### 5.4 客户端监听方式

```bash
# telnet
telnet localhost 8765

# nc (netcat)
nc localhost 8765

# 编程连接
import socket
s = socket.socket()
s.connect(("localhost", 8765))
```

### 5.5 跨语言组件

| 语言 | 组件位置 | 使用方式 |
|------|----------|----------|
| **Python** | `common/logger/python/` | `from common.logger.python import Logger` |
| Node.js | `common/logger/nodejs/` | `@Logger({port})` 装饰器 |
| Go | `common/logger/go/` | 代码生成 `go generate` |
| Rust | `common/logger/rust/` | `#[logger(port = 8765)]` 宏 |

#### Python 使用示例

```python
# 方式1: 直接使用
import sys
sys.path.insert(0, "F:/Documents/repos/projects/Agent-Tools")
from common.logger.python import Logger

logger = Logger({"port": 8765, "level": "INFO"})
logger.info("extract_start", {"file": "test.pdf"})
logger.info("extract_progress", {"current": 10, "total": 100})
logger.error("extract_failed", {"error": "file not found"})

# 方式2: 装饰器（如果工具类支持）
@Logger({"port": 8765})
class PDFTool:
    def extract(self, path):
        self.log.info("start", {"path": path})
```

> **注意**：Python logger 路径为 `common/logger/python/`，工具需要使用时从此路径引入。

## 六、模块设计

### 6.1 主入口

- 使用各语言的命令行解析库（Python: `argparse`, Node.js: `commander`, Go: `flag`）
- 支持 `--help` 查看用法
- 支持 `--config` 指定配置文件

### 6.2 独立功能模块

- 核心功能独立成模块
- 模块可单独调用
- 模块间通过参数传递数据，不重复实现

## 七、按复杂度分层

| 复杂度 | 要求 |
|--------|------|
| 简单 | README.md + .gitignore + src/ |
| 中等 | + config.json |
| 复杂 | + manual.md + MCP Server + 日志系统 + 测试 + CI |

---

**创建日期**: 2026-05-04
**更新日期**: 2026-05-05
**参考项目**: pdf2epub
