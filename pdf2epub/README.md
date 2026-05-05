# pdf2epub

> 将扫描版 PDF 转换为带页码标注的 EPUB 电子书，支持 OCR 文本校正和 LLM 智能勘校。

## 功能特性

- PDF 文本提取
- OCR 规则纠错
- LLM 智能校正（可选）
- 智能段落合并
- 页码标注
- 标准 EPUB 3.0 输出

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# MCP 模式（强烈推荐 - 生产环境使用）
python -m pdf2epub.src --mcp

# 生命周期管理
python -m pdf2epub.src --start    # 启动工具进程
python -m pdf2epub.src --status   # 查询状态
python -m pdf2epub.src --stop     # 停止工具进程
```

> **强烈推荐**：生产环境只使用 MCP 模式调用工具。单例模式确保工具进程持续运行，Claude 可精确控制生命周期。

## 目录结构

```
pdf2epub/
├── src/
│   ├── __init__.py         # 统一入口
│   ├── pdf2epub.py         # Python 实现
│   └── llm_corrector.py    # LLM 校正模块
├── config.json             # 配置文件
├── README.md              # 本文件
└── manual.md              # 详细手册
```

## 文档

- [详细手册](./manual.md)
- [Agent Tools 规范](../../AGENT_TOOL_STANDARD.md)
