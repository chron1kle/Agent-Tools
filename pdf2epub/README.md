# PDF转EPUB工具

将扫描版PDF转换为带页码标注的EPUB电子书，支持OCR文本校正和LLM智能勘校。

## 功能特性

- PDF文本提取
- OCR规则纠错
- LLM智能校正（可选）
- 智能段落合并
- 页码标注
- 标准EPUB 3.0输出

## 快速开始

```bash
# 安装依赖
pip install pypdf anthropic requests

# 配置
编辑 config.json，填写 API 密钥

# 运行
python -m src.pdf2epub input.pdf -o output
```

## 文档

- [使用手册](manual.md) - 详细使用说明

## 许可证

MIT
