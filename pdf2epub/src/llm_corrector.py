#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用LLM进行智能OCR文本校正
基于Anthropic API (参考SnE-cognitive-framework项目实现)
"""

import json
import os
import sys
import time
import argparse
import glob

try:
    from anthropic import Anthropic
except ImportError:
    print("请安装 anthropic 库: pip install anthropic")
    sys.exit(1)


# 默认配置
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 8192


def load_config(config_path: str = None) -> dict:
    """从config.json加载配置"""
    if config_path is None:
        # 查找脚本同目录下的config.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "..", "config.json")

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def get_api_config(config: dict = None) -> dict:
    """从配置中获取API相关配置"""
    if config is None:
        config = load_config()

    api_config = config.get("api", {})

    # 优先级: config > 环境变量 > 默认值
    api_key = api_config.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    return {
        "api_key": api_key,
        "model": api_config.get("model", DEFAULT_MODEL),
        "base_url": api_config.get("base_url", ""),
        "max_tokens": api_config.get("max_tokens", DEFAULT_MAX_TOKENS)
    }


class LLMCorrector:
    """LLM校正器"""

    def __init__(self, api_key: str, model: str = None, base_url: str = None, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.client = Anthropic(
            api_key=api_key,
            base_url=base_url or "https://api.anthropic.com"
        )
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens

    def create_prompt(self, text: str, page_info: str = "") -> str:
        """构建Prompt - 角色设定为专业书刊编辑"""
        return f"""你是一位专业的书刊文字编辑和校对员。你的任务是对OCR识别产生的错误文本进行精确校正。

## 校正原则
1. 修正OCR识别错误（字符错识、漏识、多识）
2. 修正错别字和标点符号错误
3. 修正因换行导致的语句断裂（OCR按行识别，需要合并为正确段落）
4. 保持原文的语义、风格和格式
5. 如果原文已经通顺，则不修改
6. **只返回校正后的文本内容，不添加任何解释、评论或格式**
7. **严格保持原文的段落结构，换行符位置不要改变**

## 上下文信息
{page_info}

## 待校正文本
```
{text}
```

## 输出要求
直接输出校正后的文本，不要添加任何前缀、后缀或说明文字。"""

    def correct(self, text: str, page_info: str = "") -> str:
        """调用LLM进行校正"""
        if not text or not text.strip():
            return text

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": self.create_prompt(text, page_info)
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"API调用错误: {e}")
            return None


def correct_json_file(
    input_path: str,
    output_path: str = None,
    api_key: str = None,
    model: str = None,
    base_url: str = None,
    start_page: int = 1,
    end_page: int = None,
    max_tokens: int = None
) -> str:
    """校正整个JSON文件"""
    # 加载配置
    config = load_config()
    api_config = get_api_config(config)

    # 参数优先级: 传入参数 > config > 环境变量 > 默认值
    api_key = api_key or api_config["api_key"]
    model = model or api_config["model"]
    base_url = base_url or api_config["base_url"]
    max_tokens = max_tokens or api_config["max_tokens"]

    if not api_key:
        print("错误: 需要在config.json中配置api_key，或设置ANTHROPIC_API_KEY环境变量")
        sys.exit(1)

    corrector = LLMCorrector(api_key, model, base_url, max_tokens)

    print(f"加载: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"共 {len(data)} 页")
    print(f"模型: {corrector.model}")
    print(f"API: {corrector.client.base_url}")

    # 确定处理范围
    pages_to_process = []
    for item in data:
        if start_page <= item['page'] <= (end_page or len(data)):
            pages_to_process.append(item)

    print(f"将处理 {len(pages_to_process)} 页")

    # 逐页处理
    for item in pages_to_process:
        page = item['page']
        text = item['text']

        if not text or not text.strip():
            print(f"Page {page}: 跳过（空内容）")
            continue

        print(f"Page {page}: 校正中 ({len(text)} 字符)...")

        page_info = f"[这是PDF第{page}页的内容]"
        corrected = corrector.correct(text, page_info)

        if corrected:
            item['text'] = corrected
            print(f"Page {page}: 完成")
        else:
            print(f"Page {page}: 失败，保留原文")

        time.sleep(0.5)  # 避免请求过快

    # 保存结果
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_llm_corrected{ext}"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n完成! 结果保存到: {output_path}")
    return output_path


def test_connection(api_key: str = None, model: str = None, base_url: str = None) -> bool:
    """测试API连接"""
    # 加载配置
    config = load_config()
    api_config = get_api_config(config)

    # 优先级: 传入参数 > config > 环境变量
    api_key = api_key or api_config["api_key"]
    model = model or api_config["model"]
    base_url = base_url or api_config["base_url"]

    if not api_key:
        print("错误: 需要在config.json中配置api_key，或设置ANTHROPIC_API_KEY环境变量")
        return False

    print("测试API连接...")
    corrector = LLMCorrector(api_key, model, base_url)

    test_text = "这是一段测试文字。"
    result = corrector.correct(test_text, "[测试]")

    if result:
        print("连接成功!")
        print(f"测试结果: {result}")
        return True
    else:
        print("连接失败")
        return False


def main():
    # 加载配置
    config = load_config()
    api_config = get_api_config(config)

    parser = argparse.ArgumentParser(description="使用LLM进行OCR文本智能校正")
    parser.add_argument("input", nargs="?", help="输入的JSON文件")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--api-key", default=api_config["api_key"], help="Anthropic API密钥")
    parser.add_argument("-m", "--model", default=api_config["model"], help="模型名称")
    parser.add_argument("--base-url", default=api_config["base_url"], help="API基础URL")
    parser.add_argument("--max-tokens", type=int, default=api_config["max_tokens"], help="最大输出token数")
    parser.add_argument("--start", type=int, default=1, help="起始页")
    parser.add_argument("--end", type=int, help="结束页")
    parser.add_argument("--test", action="store_true", help="测试API连接")
    parser.add_argument("--config", help="配置文件路径")

    args = parser.parse_args()

    # 如果指定了配置文件，重新加载
    if args.config:
        config = load_config(args.config)
        api_config = get_api_config(config)

    if args.test:
        test_connection(args.api_key or api_config["api_key"],
                       args.model or api_config["model"],
                       args.base_url or api_config["base_url"])
        return

    if not args.input:
        parser.print_help()
        return

    correct_json_file(
        args.input,
        args.output,
        args.api_key,
        args.model,
        args.base_url,
        args.start,
        args.end,
        args.max_tokens
    )


if __name__ == "__main__":
    main()
