"""模块名称: config_service
主要功能: 配置服务 - 提供统一的配置元数据提取和渲染 API

支持:
- 从 pydantic 模型提取字段元数据 (title, description, json_schema_extra)
- 将配置转换为前端可渲染的列表格式
- 配置值的类型安全更新
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Literal, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 辅助函数 ====================


def get_extra_field(field: FieldInfo, key: str, default: Any = None) -> Any:
    """从 Field 的 json_schema_extra 中提取属性

    Args:
        field: pydantic 字段信息
        key: 要提取的属性名
        default: 默认值

    Returns:
        属性值或默认值
    """
    extra = getattr(field, "json_schema_extra", None)
    if isinstance(extra, dict):
        return extra.get(key, default)
    return default


def infer_field_type(value: Any) -> str:
    """根据值推断字段类型

    Args:
        value: 字段值

    Returns:
        类型名称字符串
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "str"


def get_field_enum(field_type: Any) -> Optional[List[str]]:
    """获取 Literal 类型的枚举选项

    Args:
        field_type: 字段类型注解

    Returns:
        枚举选项列表，如果不是 Literal 则返回 None
    """
    try:
        if get_origin(field_type) is Literal:
            return list(get_args(field_type))
    except Exception:
        pass
    return None


# ==================== 配置服务类 ====================


class ConfigService:
    """配置服务

    提供 pydantic 配置模型到前端可渲染格式的转换。
    """

    @staticmethod
    def config_to_list(config_obj: BaseModel) -> List[Dict[str, Any]]:
        """将配置对象转换为前端可渲染的配置列表

        Args:
            config_obj: pydantic 配置模型实例

        Returns:
            配置项列表，每项包含 key, value, type, title, description 等
        """
        result = []

        for key, field in config_obj.model_fields.items():
            value = getattr(config_obj, key, None)

            # 跳过隐藏字段
            is_hidden = get_extra_field(field, "is_hidden", False)
            if is_hidden:
                continue

            item = {
                "key": key,
                "value": value,
                "type": infer_field_type(value),
                "title": field.title or key,
                "description": field.description or "",
                "is_secret": get_extra_field(field, "is_secret", False),
                "placeholder": get_extra_field(field, "placeholder", ""),
                "is_textarea": get_extra_field(field, "is_textarea", False),
                "overridable": get_extra_field(field, "overridable", False),
                "required": get_extra_field(field, "required", False),
            }

            # 添加枚举选项
            enum_values = get_field_enum(field.annotation)
            if enum_values:
                item["enum"] = enum_values

            result.append(item)

        return result

    @staticmethod
    def get_config_item(config_obj: BaseModel, key: str) -> Optional[Dict[str, Any]]:
        """获取单个配置项

        Args:
            config_obj: 配置对象
            key: 配置项键名

        Returns:
            配置项字典，不存在则返回 None
        """
        if key not in config_obj.model_fields:
            return None

        field = config_obj.model_fields[key]
        value = getattr(config_obj, key, None)

        return {
            "key": key,
            "value": value,
            "type": infer_field_type(value),
            "title": field.title or key,
            "description": field.description or "",
            "is_secret": get_extra_field(field, "is_secret", False),
            "placeholder": get_extra_field(field, "placeholder", ""),
        }

    @staticmethod
    def set_config_value(
        config_obj: BaseModel, key: str, value: str
    ) -> tuple[bool, str]:
        """设置配置项值

        Args:
            config_obj: 配置对象
            key: 配置项键名
            value: 新值 (字符串形式)

        Returns:
            (成功标志, 错误消息)
        """
        if key not in config_obj.model_fields:
            return False, f"配置项 {key} 不存在"

        try:
            current_value = getattr(config_obj, key)

            # 根据类型转换值
            if isinstance(current_value, bool):
                if value.lower() in ["true", "1", "yes", "t", "y"]:
                    setattr(config_obj, key, True)
                elif value.lower() in ["false", "0", "no", "f", "n"]:
                    setattr(config_obj, key, False)
                else:
                    return False, "布尔值只能是 true 或 false"
            elif isinstance(current_value, int):
                setattr(config_obj, key, int(value))
            elif isinstance(current_value, float):
                setattr(config_obj, key, float(value))
            elif isinstance(current_value, str):
                setattr(config_obj, key, value)
            elif isinstance(current_value, list):

                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    return False, "输入必须是有效的列表格式"
                setattr(config_obj, key, parsed)
            elif isinstance(current_value, dict):

                parsed = json.loads(value)
                if not isinstance(parsed, dict):
                    return False, "输入必须是有效的对象格式"
                setattr(config_obj, key, parsed)
            else:
                return False, f"不支持的配置类型: {type(current_value)}"

        except ValueError as e:
            return False, f"配置值类型错误: {e}"
        except Exception as e:
            return False, f"设置配置值时发生错误: {e}"

        return True, ""


# 便捷方法导出
config_to_list = ConfigService.config_to_list
get_config_item = ConfigService.get_config_item
set_config_value = ConfigService.set_config_value
