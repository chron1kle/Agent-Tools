# PDF转EPUB工具 - 详细手册

## 一、工具概述

本工具用于将扫描版PDF转换为带页码标注的EPUB电子书。适用于：
- 扫描版PDF的文字提取
- OCR识别后的文本校正
- 生成可编辑的EPUB电子书

## 二、目录结构

```
pdfocr-extract/
├── config.json          # 配置文件
├── README.md            # 简要介绍
├── manual.md           # 本手册
├── .gitignore         # Git忽略配置
├── src/
│   ├── __init__.py
│   ├── pdf2epub.py    # 主入口
│   └── llm_corrector.py  # LLM校正模块
└── epub_output/       # 生成的EPUB结构
```

## 三、配置文件

编辑 `config.json`：

```json
{
  "api": {
    "api_key": "sk-ant-...",  // 必填
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
  }
}
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `api.api_key` | Anthropic API密钥 |
| `api.model` | 使用的模型 |
| `correction.use_llm` | 是否启用LLM校正 |
| `correction.llm_start_page` | LLM校正起始页 |
| `correction.llm_end_page` | LLM校正结束页（null=最后一页） |
| `epub.add_page_markers` | 是否添加页码标注 |
| `output.default_dir` | 输出目录（默认：out） |

## 四、使用方法

### 4.1 一键转换

```bash
python -m src.pdf2epub 输入.pdf -t "书名" -a "作者"  # 输出默认到 out 目录
python -m src.pdf2epub 输入.pdf -o 输出目录 -t "书名" -a "作者"  # 指定输出目录
```

### 4.2 带LLM校正

```bash
python -m src.pdf2epub 输入.pdf --use-llm -t "书名"
```

### 4.3 分步执行

```bash
# 步骤1: 提取文本
python -m src.pdf2epub input.pdf --step1-extract

# 步骤2: 规则纠错
python -m src.pdf2epub input.json --step2-correct

# 步骤3: 生成EPUB
python -m src.pdf2epub input.json --step3-epub
```

### 4.4 单独使用LLM校正

```bash
python -m src.llm_corrector input.json -o output.json
```

## 五、处理流程

```
PDF → 文本提取 → 规则纠错 → LLM校正 → 段落合并 → EPUB生成
```

### 5.1 文本提取

使用 pypdf 库提取每页文本，输出JSON格式：

```json
[
  {"page": 1, "text": "第一页内容..."},
  {"page": 2, "text": "第二页内容..."}
]
```

### 5.2 规则纠错

基于正则表达式的常见OCR错误修正：
- `r` → `了`
- `「` → `"`
- `İ` → `不`
- `H己` → `自己`

### 5.3 LLM校正

使用Anthropic API进行语义级校正：
- 角色设定：专业书刊编辑
- 修正OCR错误
- 合并断裂句子
- 保持原文风格

### 5.4 段落合并

基于句子结束符判断是否合并：
- 结束符：`。！？.!?`
- 相邻行未以结束符结尾 → 合并

### 5.5 页码标注

每一页的第一个段落末尾添加 `[Page.X]`

## 六、命令行参数

### pdf2epub.py

| 参数 | 说明 |
|------|------|
| `input` | 输入文件 (PDF或JSON) |
| `-o, --output` | 输出目录 |
| `-t, --title` | 书籍标题 |
| `-a, --author` | 书籍作者 |
| `-c, --chapters` | 章节定义 |
| `--use-llm` | 使用LLM校正 |
| `--no-correction` | 跳过规则纠错 |
| `--no-page-markers` | 不添加页码标注 |
| `--step1-extract` | 只提取文本 |
| `--step2-correct` | 只规则纠错 |
| `--step3-epub` | 只生成EPUB |

### llm_corrector.py

| 参数 | 说明 |
|------|------|
| `input` | 输入JSON文件 |
| `-o, --output` | 输出文件 |
| `--api-key` | API密钥 |
| `-m, --model` | 模型名称 |
| `--start` | 起始页 |
| `--end` | 结束页 |
| `--test` | 测试API连接 |

## 七、常见问题

### Q1: 如何获取API密钥？

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 创建API密钥
3. 填入 `config.json` 的 `api.api_key` 字段

### Q2: LLM校正失败怎么办？

检查：
1. API密钥是否正确
2. 网络是否正常
3. 账户是否有足够额度

### Q3: 页码标注位置不对？

页码标注在每页第一个段落末尾。如果需要调整，修改 `create_chapter_html` 函数。

## 八、输出文件

### 8.1 中间文件

| 文件 | 说明 |
|------|------|
| `*.json` | PDF原始文本 |
| `*_corrected.json` | 规则纠错后 |
| `*_llm.json` | LLM校正后 |

### 8.2 EPUB结构

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

**版本**: 1.0  
**更新**: 2026-05-04
