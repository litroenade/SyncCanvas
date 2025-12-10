"""模块名称: tools
主要功能: AI Engine 工具注册和管理

管理 Agent 可用的工具函数，支持:
- 自动生成 OpenAI Function Calling JSON Schema
- 参数验证
- 安全检查
- 工具分类和权限控制
"""

from __future__ import annotations

import inspect
import re
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type

from pydantic import BaseModel, ValidationError

from src.logger import get_logger

logger = get_logger(__name__)


# ==================== 工具分类 ====================

class ToolCategory(Enum):
    """工具分类"""
    CANVAS = "canvas"       # 画布操作
    WEB = "web"             # 网络请求
    GENERAL = "general"     # 通用工具
    SYSTEM = "system"       # 系统工具
    DANGEROUS = "dangerous" # 危险操作 (需要确认)


# ==================== 工具元数据 ====================

class ToolMetadata:
    """工具元数据
    
    存储工具的额外信息，用于权限控制和文档生成。
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.GENERAL,
        args_schema: Optional[Type[BaseModel]] = None,
        requires_room: bool = False,
        requires_auth: bool = False,
        timeout: float = 30.0,
        retries: int = 2,
        dangerous: bool = False,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.args_schema = args_schema
        self.requires_room = requires_room
        self.requires_auth = requires_auth
        self.timeout = timeout
        self.retries = retries
        self.dangerous = dangerous


# ==================== 参数验证 ====================

class ToolValidator:
    """工具参数验证器"""

    # 危险字符串模式 (防止注入)
    DANGEROUS_PATTERNS = [
        r"__\w+__",          # Python 双下划线
        r"import\s+",        # import 语句
        r"exec\s*\(",        # exec 调用
        r"eval\s*\(",        # eval 调用
        r"os\.",             # os 模块
        r"sys\.",            # sys 模块
        r"subprocess",       # subprocess 模块
        r"open\s*\(",        # 文件操作
    ]

    # URL 白名单模式
    URL_WHITELIST = [
        r"^https?://",       # HTTP/HTTPS
    ]

    # URL 黑名单模式
    URL_BLACKLIST = [
        r"localhost",
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"192\.168\.",
        r"10\.",
        r"172\.(1[6-9]|2[0-9]|3[0-1])\.",
    ]

    @classmethod
    def validate_string(cls, value: str, field_name: str = "value") -> None:
        """验证字符串是否安全
        
        Args:
            value: 要验证的字符串
            field_name: 字段名 (用于错误信息)
            
        Raises:
            ValueError: 包含危险模式
        """
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"参数 {field_name} 包含不允许的内容")

    @classmethod
    def validate_url(cls, url: str) -> None:
        """验证 URL 是否安全
        
        Args:
            url: 要验证的 URL
            
        Raises:
            ValueError: URL 不安全
        """
        # 检查白名单
        if not any(re.match(p, url) for p in cls.URL_WHITELIST):
            raise ValueError("URL 必须以 http:// 或 https:// 开头")

        # 检查黑名单
        for pattern in cls.URL_BLACKLIST:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("不允许访问内网地址")

    @classmethod
    def validate_args(
        cls,
        args: Dict[str, Any],
        schema: Optional[Type[BaseModel]] = None,
        check_strings: bool = True,
    ) -> Dict[str, Any]:
        """验证并清理工具参数
        
        Args:
            args: 原始参数
            schema: Pydantic 模型 (可选)
            check_strings: 是否检查字符串安全性
            
        Returns:
            验证后的参数
            
        Raises:
            ValueError: 参数无效
        """
        # Pydantic 验证
        if schema:
            try:
                validated = schema(**args)
                args = validated.model_dump()
            except ValidationError as e:
                errors = e.errors()
                msg = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in errors[:3])
                raise ValueError(f"参数验证失败: {msg}") from e

        # 字符串安全检查
        if check_strings:
            for key, value in args.items():
                if isinstance(value, str):
                    cls.validate_string(value, key)

        return args


# ==================== 工具注册表 ====================

class ToolRegistry:
    """工具注册表
    
    管理所有注册的工具，支持:
    - 装饰器注册
    - 参数验证
    - Schema 生成
    - 分类管理
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._disabled_tools: Set[str] = set()

    def register(
        self,
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]] = None,
        category: ToolCategory = ToolCategory.GENERAL,
        requires_room: bool = False,
        timeout: float = 30.0,
        retries: int = 2,
        validate_args: bool = True,
        dangerous: bool = False,
    ):
        """装饰器: 注册工具函数
        
        Args:
            name: 工具名称
            description: 工具描述
            args_schema: 参数 Schema (Pydantic 模型)
            category: 工具分类
            requires_room: 是否需要房间上下文
            timeout: 执行超时 (秒)
            retries: 重试次数
            validate_args: 是否验证参数
            dangerous: 是否为危险操作
        """
        def decorator(func: Callable) -> Callable:
            # 保存元数据
            meta = ToolMetadata(
                name=name,
                description=description,
                category=category,
                args_schema=args_schema,
                requires_room=requires_room,
                timeout=timeout,
                retries=retries,
                dangerous=dangerous,
            )
            self._metadata[name] = meta

            # 包装函数添加验证
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 参数验证
                if validate_args and args_schema:
                    # 过滤掉 context 参数
                    tool_kwargs = {k: v for k, v in kwargs.items() if k != "context"}
                    try:
                        ToolValidator.validate_args(tool_kwargs, args_schema)
                    except ValueError as e:
                        return {"status": "error", "message": str(e)}

                return await func(*args, **kwargs)

            self._tools[name] = wrapper

            # 生成 Schema
            schema = self._generate_schema(name, description, args_schema, func)
            self._schemas[name] = schema

            logger.debug("注册工具: %s (%s)", name, category.value)
            return wrapper

        return decorator

    def _generate_schema(
        self,
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]],
        func: Callable,
    ) -> Dict[str, Any]:
        """生成 OpenAI Function Calling Schema"""
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

        if args_schema:
            model_schema = args_schema.model_json_schema()
            # 处理 $defs 引用
            defs = model_schema.pop("$defs", {})
            props = model_schema.get("properties", {})

            # 展开引用
            for prop_name, prop_value in props.items():
                if "$ref" in prop_value:
                    ref_name = prop_value["$ref"].split("/")[-1]
                    if ref_name in defs:
                        props[prop_name] = defs[ref_name]

            schema["function"]["parameters"] = {
                "type": "object",
                "properties": props,
                "required": model_schema.get("required", [])
            }
        else:
            # 从函数签名推断
            sig = inspect.signature(func)
            props = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name in ["self", "context"]:
                    continue

                # 推断类型
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    param_type = type_map.get(param.annotation, "string")

                props[param_name] = {"type": param_type}

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            schema["function"]["parameters"]["properties"] = props
            schema["function"]["parameters"]["required"] = required

        return schema

    def get_tool(self, name: str) -> Optional[Callable]:
        """获取工具函数"""
        if name in self._disabled_tools:
            return None
        return self._tools.get(name)

    def get_definitions(
        self,
        categories: Optional[List[ToolCategory]] = None
        ) -> List[Dict[str, Any]]:
        """获取工具定义列表
        
        Args:
            categories: 过滤分类 (可选)
            
        Returns:
            符合条件的工具定义列表
        """
        if categories is None:
            return [
                self._schemas[name]
                for name in self._schemas
                if name not in self._disabled_tools
            ]

        return [
            self._schemas[name]
            for name, meta in self._metadata.items()
            if meta.category in categories and name not in self._disabled_tools
        ]

    def get_all_tools(self) -> Dict[str, Callable]:
        """获取所有工具"""
        return {
            name: func
            for name, func in self._tools.items()
            if name not in self._disabled_tools
        }

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._metadata.get(name)

    def disable_tool(self, name: str) -> None:
        """禁用工具"""
        self._disabled_tools.add(name)
        logger.info("禁用工具: %s", name)

    def enable_tool(self, name: str) -> None:
        """启用工具"""
        self._disabled_tools.discard(name)
        logger.info("启用工具: %s", name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具信息"""
        return [
            {
                "name": name,
                "description": meta.description,
                "category": meta.category.value,
                "requires_room": meta.requires_room,
                "dangerous": meta.dangerous,
                "enabled": name not in self._disabled_tools,
            }
            for name, meta in self._metadata.items()
        ]


# ==================== 全局注册表实例 ====================

registry = ToolRegistry()
