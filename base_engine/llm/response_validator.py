"""Response validator - API 回调检验"""

import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable

from llm.llm_client import LLMResponse


@dataclass
class ValidationCriteria:
    """检验标准"""
    type: str                    # json / schema / custom
    spec: Dict[str, Any]         # 检验规格
    max_retries: int = 3


@dataclass
class ValidationResult:
    """检验结果"""
    valid: bool
    error: Optional[str] = None
    data: Optional[Any] = None


class JSONValidator:
    """JSON 格式验证器"""

    def validate(self, content: str, spec: Dict[str, Any]) -> tuple:
        """验证 JSON 格式

        Returns:
            (is_valid, error_message)
        """
        try:
            data = json.loads(content)
            return True, None, data
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {e}", None


class SchemaValidator:
    """Schema 验证器（简单实现）"""

    def validate(self, content: str, spec: Dict[str, Any]) -> tuple:
        """验证 Schema

        简单实现：只检查必需字段和类型
        """
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {e}", None

        errors = []

        # 检查必需字段
        required = spec.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # 检查字段类型
        properties = spec.get("properties", {})
        for field, field_spec in properties.items():
            if field in data:
                expected_type = field_spec.get("type")
                actual_type = type(data[field]).__name__

                # 类型映射
                type_map = {
                    "string": "str",
                    "number": "float",
                    "integer": "int",
                    "boolean": "bool",
                    "object": "dict",
                    "array": "list",
                }
                expected_python_type = type_map.get(expected_type, expected_type)

                if expected_python_type and expected_python_type != actual_type:
                    errors.append(f"Field '{field}' expected {expected_type}, got {actual_type}")

                # 检查 enum
                if "enum" in field_spec:
                    if data[field] not in field_spec["enum"]:
                        errors.append(f"Field '{field}' value not in enum: {field_spec['enum']}")

        if errors:
            return False, "; ".join(errors), None

        return True, None, data


class CustomValidator:
    """自定义验证器"""

    def __init__(self, validator_fn: Callable[[str], tuple] = None):
        self.validator_fn = validator_fn or (lambda x: (True, None, x))

    def validate(self, content: str, spec: Dict[str, Any]) -> tuple:
        """执行自定义验证函数"""
        return self.validator_fn(content)


class ResponseValidator:
    """API 回调检验系统"""

    def __init__(self):
        self.validators = {
            "json": JSONValidator(),
            "schema": SchemaValidator(),
        }

    def register_validator(self, name: str, validator):
        """注册验证器"""
        self.validators[name] = validator

    def validate(
        self,
        response: LLMResponse,
        criteria: ValidationCriteria,
    ) -> ValidationResult:
        """检验 API 回调结果

        Args:
            response: LLM 返回
            criteria: 检验标准

        Returns:
            ValidationResult
        """
        validator = self.validators.get(criteria.type)

        if not validator:
            return ValidationResult(
                valid=False,
                error=f"Unknown validator type: {criteria.type}"
            )

        try:
            is_valid, error, data = validator.validate(
                response.content,
                criteria.spec
            )
            return ValidationResult(
                valid=is_valid,
                error=error,
                data=data if is_valid else None
            )

        except Exception as e:
            return ValidationResult(valid=False, error=str(e))

    def should_retry(self, result: ValidationResult, max_retries: int) -> bool:
        """判断是否需要重试"""
        if result.valid:
            return False

        # 只有格式错误或超时才重试
        retryable_errors = {"format_error", "timeout"}
        return (
            result.error in retryable_errors or
            "JSON decode error" in (result.error or "")
        ) and max_retries > 0


# 模块级单例
response_validator = ResponseValidator()
