# pdf2epub 详细手册

## 一、工具概述

本工具用于将扫描版 PDF 转换为带页码标注的 EPUB 电子书。适用于：
- 扫描版 PDF 的文字提取
- OCR 识别后的文本校正
- 生成可编辑的 EPUB 电子书

## 二、目录结构

```
pdf2epub/
├── src/
│   ├── __init__.py         # 统一入口
│   ├── pdf2epub.py        # 主实现
│   └── llm_corrector.py   # LLM 校正模块
├── config.json             # 配置文件
├── README.md              # 简要介绍
└── manual.md              # 本文件
```

## 三、配置文件

编辑 `config.json`：

```json
{
  "version": "1.0",
  "description": "PDF 转 EPUB 工具",
  "log": {
    "enabled": true,
    "host": "localhost",
    "port": 8765,
    "level": "INFO"
  },
  "api": {
    "api_key": "sk-ant-...",
    "model": "claude-sonnet-4-20250514",
    "base_url": "",
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
    "default_author": "Unknown"
  },
  "output": {
    "default_dir": "out"
  }
}
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `api.api_key` | Anthropic API 密钥 |
| `api.model` | 使用的模型 |
| `correction.use_llm` | 是否启用 LLM 校正 |
| `correction.llm_start_page` | LLM 校正起始页 |
| `correction.llm_end_page` | LLM 校正结束页（null=最后一页） |
| `epub.add_page_markers` | 是否添加页码标注 |
| `output.default_dir` | 输出目录（默认：out） |
| `log.port` | 日志端口 |

## 四、使用方法

> **强烈推荐**：生产环境只使用 MCP 模式调用工具。单例模式确保工具进程持续运行，Claude 可精确控制生命周期。

### 4.1 生命周期管理

```bash
# 启动工具进程
python -m pdf2epub.src --start

# 查询状态
python -m pdf2epub.src --status

# 停止工具进程
python -m pdf2epub.src --stop

# 重启工具进程
python -m pdf2epub.src --restart
```

### 4.2 MCP 模式

```bash
# 启动 MCP 服务器
python -m pdf2epub.src --mcp
```

MCP 模式启动后，LLM 可以通过 MCP 协议调用此工具。

### 4.3 命令行模式（仅开发调试用）

```bash
# 基本转换
python -m pdf2epub.src input.pdf -o output

# 指定书名和作者
python -m pdf2epub.src input.pdf -t "书名" -a "作者"

# 带 LLM 校正
python -m pdf2epub.src input.pdf --use-llm

# 分步执行
python -m pdf2epub.src input.pdf --step1-extract   # 只提取文本
python -m pdf2epub.src input.pdf --step2-correct   # 只规则纠错
python -m pdf2epub.src input.pdf --step3-epub      # 只生成 EPUB
```

### 4.4 编程调用

```python
from pdf2epub.src import run

result = run("input.pdf", "--output", "out")
```

## 五、处理流程

```
PDF → 文本提取 → 规则纠错 → LLM校正 → 段落合并 → EPUB生成
```

### 5.1 文本提取

使用 pypdf 库提取每页文本，输出 JSON 格式：

```json
[
  {"page": 1, "text": "第一页内容..."},
  {"page": 2, "text": "第二页内容..."}
]
```

### 5.2 规则纠错

基于正则表达式的常见 OCR 错误修正：
- `r` → `了`
- `「` → `"`
- `İ` → `不`
- `H己` → `自己`

### 5.3 LLM 校正

使用 Anthropic API 进行语义级校正：
- 角色设定：专业书刊编辑
- 修正 OCR 错误
- 合并断裂句子
- 保持原文风格

### 5.4 段落合并

基于句子结束符判断是否合并：
- 结束符：`。！？.!?`
- 相邻行未以结束符结尾 → 合并

### 5.5 页码标注

每一页的第一个段落末尾添加 `[Page.X]`

## 六、命令行参数

| 参数 | 说明 |
|------|------|
| `input` | 输入文件 (PDF 或 JSON) |
| `-o, --output` | 输出目录 |
| `-t, --title` | 书籍标题 |
| `-a, --author` | 书籍作者 |
| `-c, --chapters` | 章节定义 |
| `--use-llm` | 使用 LLM 校正 |
| `--no-correction` | 跳过规则纠错 |
| `--no-page-markers` | 不添加页码标注 |
| `--step1-extract` | 只提取文本 |
| `--step2-correct` | 只规则纠错 |
| `--step3-epub` | 只生成 EPUB |

## 七、常见问题

### Q1: 如何获取 API 密钥？

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 创建 API 密钥
3. 填入 `config.json` 的 `api.api_key` 字段

### Q2: LLM 校正失败怎么办？

检查：
1. API 密钥是否正确
2. 网络是否正常
3. 账户是否有足够额度

### Q3: 页码标注位置不对？

页码标注在每页第一个段落末尾。如果需要调整，修改 `create_chapter_html` 函数。

## 八、输出文件

### 8.1 中间文件

| 文件 | 说明 |
|------|------|
| `*.json` | PDF 原始文本 |
| `*_corrected.json` | 规则纠错后 |
| `*_llm.json` | LLM 校正后 |

### 8.2 EPUB 结构

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

## 九、依赖

```
pypdf>=4.0.0
anthropic>=0.20.0
requests>=2.28.0
```

---

**版本**: 2.0
**更新**: 2026-05-05
