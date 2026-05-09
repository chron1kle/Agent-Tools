"""
Engine 启动检查脚本

用途：验证环境配置是否正常（配置加载、API 连接、依赖安装等）
不检查代码本身的语法或逻辑问题

执行方式：
    python test/check_env.py
"""

import asyncio
import importlib
import json
import os
import sys
from dataclasses import dataclass

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, os.path.join(project_root, "base_engine"))
sys.path.insert(0, os.path.join(project_root, "engine", "src"))

from llm import llm_client


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str


# ─── 依赖检查 ───

REQUIRED_PACKAGES = [
    ("httpx", "HTTP 客户端，LLM API 调用必需"),
    ("anthropic", "Anthropic API 客户端（如果使用 Anthropic 模型）"),
    ("openai", "OpenAI API 客户端（如果使用 OpenAI 模型）"),
]


def check_python_version() -> CheckResult:
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return CheckResult("Python 版本", False, f"{version.major}.{version.minor} 不满足要求（需 >= 3.8）")
    return CheckResult("Python 版本", True, f"{version.major}.{version.minor}.{version.micro}")


def check_package(package_name: str) -> CheckResult:
    """检查单个包是否安装"""
    try:
        mod = importlib.import_module(package_name)
        version = getattr(mod, "__version__", "unknown")
        return CheckResult(f"依赖包 [{package_name}]", True, f"已安装 (version: {version})")
    except ImportError:
        return CheckResult(f"依赖包 [{package_name}]", False, "未安装")


def check_dependencies() -> list[CheckResult]:
    """检查所有必需依赖"""
    results = [check_python_version()]
    for pkg, _ in REQUIRED_PACKAGES:
        results.append(check_package(pkg))
    return results


# ─── 配置检查 ───

def check_config_file() -> CheckResult:
    """检查 config.json 是否存在且格式正确"""
    config_path = os.path.join(project_root, "engine", "config.json")
    if not os.path.exists(config_path):
        return CheckResult("config.json 存在性", False, f"文件不存在: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "llm" not in config or "model_types" not in config["llm"]:
            return CheckResult("config.json 格式", False, "缺少 llm.model_types 字段")
        return CheckResult("config.json 格式", True, f"包含 {len(config['llm']['model_types'])} 个模型类型")
    except json.JSONDecodeError as e:
        return CheckResult("config.json 格式", False, f"JSON 解析失败: {e}")


def check_model_types_loaded() -> CheckResult:
    """检查模型类型是否加载"""
    with open(os.path.join(project_root, "engine", "config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)

    llm_config = config.get("llm", {})
    llm_client.load_config(llm_config)

    model_types = list(llm_client.registry._models.keys())
    if not model_types:
        return CheckResult("模型类型加载", False, "没有加载任何模型类型")

    return CheckResult("模型类型加载", True, f"已加载: {', '.join(model_types)}")


# ─── API 连接检查 ───

def check_api_connectivity(model_type: str, test_message: str = "Hello") -> CheckResult:
    """检查 API 是否可连接"""
    try:
        config = llm_client.registry.resolve(model_type)
    except Exception as e:
        return CheckResult(f"API 连接 [{model_type}]", False, f"无法解析模型配置: {e}")

    try:
        from llm import CallOptions
        from llm.llm_client import LLMResponse

        async def _test():
            opts = CallOptions(
                model_type=model_type,
                max_retries=1,
                temperature=0.5,
            )
            messages = [{"role": "user", "content": test_message}]
            response: LLMResponse = await llm_client.chat(messages, opts)
            return response

        response = asyncio.run(_test())
        if response and response.content:
            return CheckResult(
                f"API 连接 [{model_type}]",
                True,
                f"成功 | 模型: {response.model} | 响应: {response.content[:50]}..."
            )
        else:
            return CheckResult(f"API 连接 [{model_type}]", False, "响应内容为空")

    except Exception as e:
        return CheckResult(f"API 连接 [{model_type}]", False, f"调用失败: {e}")


# ─── 运行 ───

def run_checks():
    """运行所有检查"""
    print("=" * 60)
    print("Engine 启动检查")
    print("=" * 60)
    print()

    results: list[CheckResult] = []

    # 1. 依赖检查
    print("[1/3] 检查依赖...")
    dep_results = check_dependencies()
    results.extend(dep_results)

    # 2. 配置检查
    print("[2/3] 检查配置...")
    results.append(check_config_file())
    results.append(check_model_types_loaded())

    # 3. API 连接检查
    print("[3/3] 检查 API 连接...")
    model_types = list(llm_client.registry._models.keys())
    for model_type in model_types:
        result = check_api_connectivity(model_type)
        results.append(result)

    # 输出结果
    print()
    print("=" * 60)
    print("检查结果")
    print("=" * 60)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}")
        print(f"       {result.message}")
        print()

    # 总结
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print("=" * 60)
    print(f"总结: {passed}/{total} 项通过")

    if passed < total:
        print("\n有检查项失败，请检查配置和环境")
        sys.exit(1)
    else:
        print("\n所有检查通过，环境正常")
        sys.exit(0)


if __name__ == "__main__":
    run_checks()
