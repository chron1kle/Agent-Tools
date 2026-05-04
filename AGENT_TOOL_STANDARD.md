# Agent Tool 构建规范

> **版本**: 1.0
> **适用场景**: AI Agent 工具类项目的标准化结构

---

## 一、目录结构

```
project-name/
├── config.json          # 配置文件（必选）
├── README.md            # 简要介绍（必选）
├── manual.md           # 详细手册（必选）
├── .gitignore         # Git忽略配置（必选）
├── src/               # 源代码目录（必选）
│   ├── __init__.py    # 包初始化文件
│   └── *.py           # 功能模块
└── epub_output/       # 输出结构模板（可选）
```

## 二、文件规范

### 2.1 config.json

必需字段：

```json
{
  "version": "1.0",
  "description": "项目描述",
  "api": {
    "provider": "服务商名称",
    "api_key": "",
    "base_url": "",
    "model": "模型名称",
    "max_tokens": 8192
  },
  "correction": {
    "use_rule_based": true,
    "use_llm": false,
    "llm_start_page": 1,
    "llm_end_page": null
  },
  "epub": {
    "add_page_markers": true,
    "default_author": "Unknown",
    "chapters": []
  },
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

标准Python项目忽略配置：
- `__pycache__/`
- `*.py[cod]`
- `venv/`, `env/`
- `.idea/`, `.vscode/`
- `out/`, `*.epub`, `*.pdf`
- `.env`, `*.log`

### 2.5 src/__init__.py

包初始化文件，至少包含项目名称注释。

## 三、代码规范

### 3.1 配置文件加载

```python
import os
import json

def load_config(config_path: str = None) -> dict:
    """从config.json加载配置"""
    if config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "config.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
```

### 3.2 API配置获取

```python
def get_api_config(config: dict = None) -> dict:
    """从配置中获取API相关配置"""
    if config is None:
        config = load_config()
    
    api_config = config.get("api", {})
    
    # 优先级: config > 环境变量 > 默认值
    api_key = api_config.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    
    return {
        "api_key": api_key,
        "model": api_config.get("model", "default-model"),
        "base_url": api_config.get("base_url", ""),
        "max_tokens": api_config.get("max_tokens", 8192)
    }
```

## 四、模块设计

### 4.1 主入口模块

- 使用 `argparse` 处理命令行参数
- 支持 `--step1`, `--step2`, `--step3` 分步执行
- 支持 `--use-llm` 启用LLM校正
- 支持 `--config` 指定配置文件

### 4.2 独立功能模块

- LLM校正、文本处理等功能独立成模块
- 模块可单独调用
- 模块间通过参数传递数据，不重复实现

## 五、输出格式

### 5.1 EPUB结构

```
epub_output/
├── mimetype
├── META-INF/
│   └── container.xml
└── OEBPS/
    ├── style.css
    ├── nav.xhtml
    ├── content.opf
    └── chapter_*.xhtml
```

### 5.2 中间文件

| 文件 | 说明 |
|------|------|
| `*.json` | 原始提取文本 |
| `*_corrected.json` | 规则纠错后 |
| `*_llm.json` | LLM校正后 |

---

**创建日期**: 2026-05-04
**参考项目**: pdfocr-extract
