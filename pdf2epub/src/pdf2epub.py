#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文本提取、OCR纠错、EPUB生成一体化工具
用于处理扫描版PDF，生成带页码标注的EPUB
"""

import json
import os
import re
import sys
import argparse
import time
import threading
from html import escape


# ============== 进度报告 ==============

class ProgressReporter:
    """进度报告器 - 每秒输出 JSON 进度"""

    def __init__(self):
        self.progress = 0.0
        self.message = ""
        self._last_report_time = 0
        self._report_interval = 1.0  # 每秒报告一次

    def update(self, progress: float, message: str = ""):
        """更新进度"""
        self.progress = progress
        self.message = message
        self._report()

    def _report(self):
        """输出进度到 stdout（JSON 格式）"""
        current_time = time.time()
        if current_time - self._last_report_time >= self._report_interval:
            self._last_report_time = current_time
            output = {
                "type": "progress",
                "progress": self.progress,
                "message": self.message
            }
            print(json.dumps(output, ensure_ascii=False))

    def done(self, message: str = "完成"):
        """完成"""
        self.update(100.0, message)


# 全局进度报告器
progress = ProgressReporter()


# ============== 配置管理 ==============

def load_config(config_path: str = None) -> dict:
    """从config.json加载配置"""
    if config_path is None:
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
    api_key = api_config.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    return {
        "api_key": api_key,
        "model": api_config.get("model", "claude-sonnet-4-20250514"),
        "base_url": api_config.get("base_url", ""),
        "max_tokens": api_config.get("max_tokens", 8192)
    }


def get_output_config(config: dict = None) -> dict:
    """从配置中获取输出相关配置"""
    if config is None:
        config = load_config()

    output_config = config.get("output", {})
    return {
        "default_dir": output_config.get("default_dir", "out")
    }

# ============== 第一部分：PDF文本提取 ==============

def extract_text_json(pdf_path):
    """提取为JSON格式，每页一个对象"""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("错误: 请安装 pypdf 库 (pip install pypdf)")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    result = []

    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        result.append({
            "page": i,
            "text": text.strip() if text else ""
        })

    return result


def extract_text_txt(pdf_path, separator="[--- Page {} ---]"):
    """提取为带页码分隔的文本格式"""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("错误: 请安装 pypdf 库 (pip install pypdf)")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    lines = []

    for i, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            lines.append(separator.format(i))
            lines.append(text.strip())
            lines.append("")

    return "\n".join(lines)


# ============== 第二部分：OCR纠错 ==============

# OCR错误纠错规则
CORRECTION_RULES = [
    # 标点符号
    (r'「', '"'),
    (r'」', '"'),
    (r'〔', '['),
    (r'〕', ']'),
    (r'〈', '<'),
    (r'〉', '>'),
    (r'【', '['),
    (r'】', ']'),

    # 常见字符错误
    (r'\br\b', '了'),
    (r'成r', '成了'),
    (r'İ', '不'),
    (r'ï', '以'),
    (r'ϵ', '以'),
    (r'ȡ', '取'),
    (r'ȱ', '乏'),
    (r'ľ', '存'),
    (r'Ľ', '性'),
    (r'Ŀ', '目'),
    (r'ǿ', '强'),
    (r'Ⱥ', '具'),
    (r'Ǳ', '整'),
    (r'Ĵ', '时'),
    (r'Ĳ', '际'),
    (r'ǚ', '运'),
    (r'ń', '已'),
    (r'Ĺ', '死'),

    # 常见词语错误
    (r'门动', '自动'),
    (r'对丁', '对'),
    (r'ill', '做'),
    (r'ın', '不'),
    (r'İn', '不'),
    (r'ïn', '不'),
    (r'“不', '不'),
    (r'H己', '自己'),

    # 清理
    (r'\.{2,}', '。'),
    (r',{2,}', '，'),
    (r'工$', '了'),
    (r'J$', '了'),
    (r'Q$', '。'),
]


def correct_text(text):
    """对文本进行OCR纠错"""
    corrected = text
    for pattern, replacement in CORRECTION_RULES:
        corrected = re.sub(pattern, replacement, corrected)
    corrected = re.sub(r' +', ' ', corrected)
    corrected = re.sub(r'\n{3,}', '\n\n', corrected)
    return corrected


def correct_json_data(data):
    """处理JSON数据"""
    for item in data:
        item['text'] = correct_text(item['text'])
    return data


# ============== 第三部分：EPUB生成 ==============

def create_page_html(text, page_num):
    """创建单页HTML"""
    paragraphs = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if line:
            if len(line) < 30 and not line.endswith(('.', '。', ',', '，', '!', '！', '?', '？')):
                paragraphs.append(f'<h2>{escape(line)}</h2>')
            else:
                paragraphs.append(f'<p>{escape(line)}</p>')

    html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>第{page_num}页</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="page">
        {''.join(paragraphs)}
    </div>
</body>
</html>'''
    return html


def is_sentence_end(text):
    """判断文本是否以句子结束符结尾"""
    text = text.strip()
    if not text:
        return False
    # 句子结束符
    end_marks = {'。', '！', '？', '.', '!', '?', '…', '~', '—', '"'}
    return text[-1] in end_marks


def merge_paragraphs(text_lines):
    """
    智能合并段落
    将OCR按行扫描的结果合并为语义正确的段落
    """
    if not text_lines:
        return []

    merged = []
    current_para = ""

    for line in text_lines:
        line = line.strip()
        if not line:
            # 空行表示段落结束
            if current_para:
                merged.append(current_para)
                current_para = ""
            continue

        if not current_para:
            current_para = line
        else:
            # 检查当前段落是否以句子结束符结尾
            if is_sentence_end(current_para):
                # 结束当前段落，开始新段落
                merged.append(current_para)
                current_para = line
            else:
                # 继续合并到当前段落
                current_para = current_para + " " + line

    # 处理最后一个段落
    if current_para:
        merged.append(current_para)

    return merged


def create_chapter_html(chapter_data, start_page, end_page, all_pages):
    """创建章节HTML，每页第一个段落标注页码"""
    title = chapter_data['title']
    content = []

    for page in all_pages:
        if start_page <= page['page'] <= end_page:
            text = page['text'].strip()
            if text:
                # 智能合并段落
                paragraphs = merge_paragraphs(text.split('\n'))
                first_para_of_page = True

                for para in paragraphs:
                    para = para.strip()
                    if para:
                        if first_para_of_page:
                            content.append(f'<p>{escape(para)} <span class="page-ref">[Page.{page["page"]}]</span></p>')
                            first_para_of_page = False
                        else:
                            content.append(f'<p>{escape(para)}</p>')

    html = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{escape(title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <section epub:type="chapter" epub:toc="auto">
        <h1 class="chapter-title">{escape(title)}</h1>
        {''.join(content)}
    </section>
</body>
</html>'''
    return html


def create_toc_xhtml(chapters):
    """创建导航目录"""
    items = []
    for i, ch in enumerate(chapters, 1):
        items.append(f'''        <navPoint id="navPoint-{i}" playOrder="{i}">
            <navLabel>
                <text>{escape(ch['title'])}</text>
            </navLabel>
            <content src="chapter_{i:02d}.xhtml"/>
        </navPoint>''')

    nav = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>目录</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>目录</h1>
        <ol>
{chr(10).join(items)}
        </ol>
    </nav>
</body>
</html>'''
    return nav


def create_style_css():
    """创建CSS样式"""
    return '''@charset "UTF-8";

body {
    font-family: "SimSun", "Songti SC", "Noto Serif CJK SC", serif;
    font-size: 1em;
    line-height: 1.8;
    margin: 0;
    padding: 1em;
    text-align: justify;
}

h1.chapter-title {
    font-size: 1.5em;
    text-align: center;
    margin: 2em 0 1em 0;
    padding-bottom: 0.5em;
    border-bottom: 1px solid #ccc;
}

h2 {
    font-size: 1.2em;
    margin: 1.5em 0 0.5em 0;
    text-align: center;
}

p {
    text-indent: 2em;
    margin: 0.3em 0;
}

p.page-num {
    text-indent: 0;
    text-align: center;
    font-size: 0.8em;
    color: #888;
    margin: 2em 0 1em 0;
}

span.page-ref {
    font-size: 0.7em;
    color: #999;
    margin-left: 0.5em;
}

nav#toc ol {
    list-style: none;
    padding-left: 0;
}

nav#toc li {
    margin: 0.5em 0;
}

nav#toc a {
    text-decoration: none;
    color: #333;
}
'''


def create_container_xml():
    """创建container.xml"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''


def create_content_opf(chapters, total_pages):
    """创建content.opf"""
    manifest_items = []
    manifest_items.append('    <item id="style" href="style.css" media-type="text/css"/>')
    manifest_items.append('    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    for i in range(1, len(chapters) + 1):
        manifest_items.append(f'    <item id="chapter_{i:02d}" href="chapter_{i:02d}.xhtml" media-type="application/xhtml+xml"/>')

    spine_items = []
    for i in range(1, len(chapters) + 1):
        spine_items.append(f'    <itemref idref="chapter_{i:02d}"/>')

    manifest = '\n'.join(manifest_items)
    spine = '\n'.join(spine_items)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>PDF转EPUB</dc:title>
        <dc:creator>Unknown</dc:creator>
        <dc:language>zh-CN</dc:language>
        <dc:identifier id="bookid">pdf-to-epub-001</dc:identifier>
        <meta property="dcterms:modified">2026-05-04T00:00:00Z</meta>
    </metadata>
    <manifest>
{manifest}
    </manifest>
    <spine>
{spine}
    </spine>
</package>'''


def generate_epub(data, output_dir, title="PDF转EPUB", author="Unknown", chapters=None):
    """生成EPUB"""
    if chapters is None:
        # 自动生成章节
        chapters = auto_generate_chapters(len(data))

    # 创建目录
    os.makedirs(output_dir, exist_ok=True)
    epub_dir = os.path.join(output_dir, 'OEBPS')
    os.makedirs(epub_dir, exist_ok=True)

    print(f"生成 {len(chapters)} 个章节...")

    # CSS
    with open(os.path.join(epub_dir, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(create_style_css())

    # 章节
    for i, ch in enumerate(chapters, 1):
        html = create_chapter_html(ch, ch['start'], ch['end'], data)
        filename = f'chapter_{i:02d}.xhtml'
        with open(os.path.join(epub_dir, filename), 'w', encoding='utf-8') as f:
            f.write(html)

    # 导航
    with open(os.path.join(epub_dir, 'nav.xhtml'), 'w', encoding='utf-8') as f:
        f.write(create_toc_xhtml(chapters))

    # OPF
    with open(os.path.join(epub_dir, 'content.opf'), 'w', encoding='utf-8') as f:
        content_opf = create_content_opf(chapters, len(data))
        # 更新标题和作者
        content_opf = content_opf.replace('PDF转EPUB', title)
        content_opf = content_opf.replace('>Unknown<', f'>{author}<')
        f.write(content_opf)

    # Container
    os.makedirs(os.path.join(output_dir, 'META-INF'), exist_ok=True)
    with open(os.path.join(output_dir, 'META-INF', 'container.xml'), 'w', encoding='utf-8') as f:
        f.write(create_container_xml())

    # Mimetype
    with open(os.path.join(output_dir, 'mimetype'), 'w', encoding='utf-8') as f:
        f.write('application/epub+zip')

    print(f"EPUB文件结构已生成: {output_dir}")
    return chapters


def auto_generate_chapters(total_pages):
    """自动生成章节（基于页数均分）"""
    chapters = []
    # 简单策略：每50页一章
    chunk_size = 50
    for i in range(0, total_pages, chunk_size):
        chapters.append({
            "title": f"第{i//chunk_size + 1}章",
            "start": i + 1,
            "end": min(i + chunk_size, total_pages)
        })
    return chapters


def load_json(json_path):
    """加载JSON文件"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data, output_path):
    """保存JSON文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_file_title(filepath):
    """从文件名提取标题"""
    basename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(basename)[0]
    # 移除常见的OCR后缀
    name_without_ext = re.sub(r'_OCR|_扫描|_pdf', '', name_without_ext, flags=re.IGNORECASE)
    return name_without_ext


# ============== 主程序 ==============

def main():
    # 加载默认配置
    config = load_config()
    output_config = get_output_config(config)
    default_output_dir = output_config.get("default_dir", "out")

    parser = argparse.ArgumentParser(
        description="PDF文本提取、OCR纠错、EPUB生成一体化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 方式1: 一键完成 (从PDF直接到EPUB)
  python pdf2epub.py 输入.pdf -o 输出目录

  # 方式2: 分步执行
  python pdf2epub.py 输入.pdf --step1-extract         # 只提取文本
  python pdf2epub.py 输入.json --step2-correct        # 只纠错
  python pdf2epub.py 输入.json --step3-epub           # 只生成EPUB

  # 方式3: 自定义章节
  python pdf2epub.py 输入.pdf -o 输出 -t "书名" -a "作者" -c "第1章,1,10|第2章,11,30"
        '''
    )

    parser.add_argument("input", help="输入文件 (PDF或JSON)")
    parser.add_argument("-o", "--output", default=default_output_dir, help="输出目录")
    parser.add_argument("-t", "--title", help="书籍标题（默认从文件名提取）")
    parser.add_argument("-a", "--author", help="书籍作者")
    parser.add_argument("-c", "--chapters", help="章节定义，格式: 标题1,起始页,结束页|标题2,...")
    parser.add_argument("--no-correction", action="store_true", help="跳过OCR纠错（规则纠错）")
    parser.add_argument("--no-page-markers", action="store_true", help="不添加页码标注")

    # LLM校正选项
    parser.add_argument("--use-llm", action="store_true", help="使用LLM进行智能校正")
    parser.add_argument("--llm-provider", choices=["anthropic", "ollama"], default="anthropic",
                        help="LLM提供者")
    parser.add_argument("--llm-api-key", help="LLM API密钥")
    parser.add_argument("--llm-model", help="LLM模型名称")
    parser.add_argument("--llm-base-url", help="API基础URL")
    parser.add_argument("--llm-start", type=int, default=1, help="LLM校正起始页")
    parser.add_argument("--llm-end", type=int, help="LLM校正结束页")

    # 步骤选项
    parser.add_argument("--step1-extract", action="store_true", help="只执行步骤1: PDF提取文本")
    parser.add_argument("--step2-correct", action="store_true", help="只执行步骤2: OCR纠错（规则）")
    parser.add_argument("--step3-epub", action="store_true", help="只执行步骤3: 生成EPUB")

    args = parser.parse_args()

    input_file = args.input
    output_dir = args.output

    # 确定输入类型
    if input_file.lower().endswith('.pdf'):
        input_type = 'pdf'
    elif input_file.lower().endswith('.json'):
        input_type = 'json'
    else:
        print(f"错误: 不支持的输入格式")
        sys.exit(1)

    # 步骤1: PDF提取
    if args.step1_extract:
        if input_type != 'pdf':
            print("错误: --step1-extract 需要PDF输入")
            sys.exit(1)
        progress.update(10.0, "正在提取 PDF 文本...")
        json_path = input_file.replace('.pdf', '.json')
        data = extract_text_json(input_file)
        progress.update(30.0, "正在保存文本...")
        save_json(data, json_path)
        progress.done("文本提取完成")
        print(f"文本已提取到: {json_path}")
        return

    # 步骤2: 纠错
    if args.step2_correct:
        if input_type != 'json':
            print("错误: --step2-correct 需要JSON输入")
            sys.exit(1)
        progress.update(40.0, "正在规则纠错...")
        data = load_json(input_file)
        data = correct_json_data(data)
        progress.update(70.0, "正在保存...")
        corrected_path = input_file.replace('.json', '_corrected.json')
        save_json(data, corrected_path)
        progress.done("纠错完成")
        print(f"纠错完成: {corrected_path}")
        return

    # 步骤3: EPUB
    if args.step3_epub:
        if input_type != 'json':
            print("错误: --step3-epub 需要JSON输入")
            sys.exit(1)
        progress.update(50.0, "正在生成 EPUB...")
        data = load_json(input_file)

        # 解析章节
        chapters = None
        if args.chapters:
            chapters = []
            for ch in args.chapters.split('|'):
                parts = ch.split(',')
                if len(parts) == 3:
                    chapters.append({
                        "title": parts[0],
                        "start": int(parts[1]),
                        "end": int(parts[2])
                    })

        # 提取标题和作者
        title = args.title or get_file_title(input_file)
        author = args.author or "Unknown"

        generate_epub(data, output_dir, title, author, chapters)
        progress.update(80.0, "正在打包 EPUB...")

        # 打包EPUB
        epub_path = os.path.join(os.path.dirname(output_dir), f"{title}.epub")
        if os.path.exists(epub_path):
            os.remove(epub_path)

        import subprocess
        subprocess.run([
            'powershell', '-Command',
            f'Compress-Archive -Path "{output_dir}\\mimetype","{output_dir}\\META-INF","{output_dir}\\OEBPS" -DestinationPath "{epub_path}" -Force'
        ], capture_output=True)

        progress.done("EPUB 生成完成")
        print(f"EPUB已生成: {epub_path}")
        return

    # 一键模式: PDF -> JSON -> 规则纠错 -> LLM校正 -> EPUB
    if input_type == 'pdf':
        progress.update(10.0, "正在从 PDF 提取文本...")
        print(f"步骤1: 从PDF提取文本...")
        json_path = os.path.join(output_dir, os.path.basename(input_file).replace('.pdf', '.json'))
        data = extract_text_json(input_file)
        save_json(data, json_path)
        progress.update(30.0, "正在 OCR 规则纠错...")

        if not args.no_correction:
            print("步骤2: OCR规则纠错...")
            data = correct_json_data(data)
            corrected_path = json_path.replace('.json', '_corrected.json')
            save_json(data, corrected_path)
            json_path = corrected_path
        progress.update(60.0, "正在生成 EPUB...")
    else:
        json_path = input_file
        data = load_json(json_path)

        if not args.no_correction:
            print("步骤2: OCR规则纠错...")
            data = correct_json_data(data)
            corrected_path = json_path.replace('.json', '_corrected.json')
            save_json(data, corrected_path)
            json_path = corrected_path

    # LLM智能校正
    if args.use_llm:
        # 加载配置
        config = load_config()
        api_config = get_api_config(config)

        # 获取校正配置
        correction_config = config.get("correction", {})

        print("步骤3: LLM智能校正...")
        try:
            from llm_correct import correct_json_file
        except ImportError:
            print("错误: 请确保 llm_correct.py 在同一目录下")
            sys.exit(1)

        # 参数优先级: 命令行参数 > config.json > 默认值
        llm_api_key = args.llm_api_key or api_config["api_key"]
        llm_model = args.llm_model or api_config["model"]
        llm_base_url = args.llm_base_url or api_config["base_url"]
        llm_start = args.llm_start or correction_config.get("llm_start_page", 1)
        llm_end = args.llm_end or correction_config.get("llm_end_page")

        if not llm_api_key:
            print("错误: 请在config.json中配置api_key，或设置ANTHROPIC_API_KEY环境变量")
            sys.exit(1)

        llm_output = json_path.replace('.json', '_llm.json')
        progress.update(70.0, "正在进行 LLM 智能校正...")
        correct_json_file(
            json_path,
            llm_output,
            api_key=llm_api_key,
            model=llm_model,
            base_url=llm_base_url,
            start_page=llm_start,
            end_page=llm_end
        )
        json_path = llm_output
        data = load_json(json_path)

        progress.update(80.0, "正在生成 EPUB...")
        print("步骤4: 生成EPUB...")
    else:
        progress.update(70.0, "正在生成 EPUB...")
        print("步骤3: 生成EPUB...")

    # 解析章节
    chapters = None
    if args.chapters:
        chapters = []
        for ch in args.chapters.split('|'):
            parts = ch.split(',')
            if len(parts) == 3:
                chapters.append({
                    "title": parts[0],
                    "start": int(parts[1]),
                    "end": int(parts[2])
                })

    # 提取标题和作者
    title = args.title or get_file_title(json_path)
    author = args.author or "Unknown"

    # 临时禁用页码标注
    if args.no_page_markers:
        # 保存原始函数引用
        orig_create_chapter_html = create_chapter_html
        # 替换为不带页码的版本
        def create_chapter_html_no_marker(chapter_data, start_page, end_page, all_pages):
            title = chapter_data['title']
            content = []
            for page in all_pages:
                if start_page <= page['page'] <= end_page:
                    text = page['text'].strip()
                    if text:
                        # 使用智能段落合并
                        paragraphs = merge_paragraphs(text.split('\n'))
                        for para in paragraphs:
                            para = para.strip()
                            if para:
                                content.append(f'<p>{escape(para)}</p>')
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{escape(title)}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <section epub:type="chapter" epub:toc="auto">
        <h1 class="chapter-title">{escape(title)}</h1>
        {''.join(content)}
    </section>
</body>
</html>'''
        globals()['create_chapter_html'] = create_chapter_html_no_marker

    generate_epub(data, output_dir, title, author, chapters)

    # 恢复原始函数
    if args.no_page_markers:
        globals()['create_chapter_html'] = orig_create_chapter_html

    # 打包EPUB
    epub_path = os.path.join(os.path.dirname(output_dir), f"{title}.epub")
    if os.path.exists(epub_path):
        os.remove(epub_path)

    import subprocess
    progress.update(90.0, "正在打包 EPUB...")
    subprocess.run([
        'powershell', '-Command',
        f'Compress-Archive -Path "{output_dir}\\mimetype","{output_dir}\\META-INF","{output_dir}\\OEBPS" -DestinationPath "{epub_path}" -Force'
    ], capture_output=True)

    progress.done("转换完成")
    print(f"\n完成! EPUB: {epub_path}")


if __name__ == "__main__":
    main()
