"""
AI Engine Core: Tool Registry
Manages the registration and retrieval of tools (functions) available to agents.
Supports auto-generation of JSON schemas for OpenAI function calling.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, create_model


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, args_schema: Type[BaseModel] = None):
        """
        Decorator to register a function as a tool.
        """
        def decorator(func: Callable):
            self._tools[name] = func
            
            # Generate Schema
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
                schema["function"]["parameters"] = {
                    "type": "object",
                    "properties": model_schema.get("properties", {}),
                    "required": model_schema.get("required", [])
                }
            else:
                # Simple introspection fallback (less robust)
                sig = inspect.signature(func)
                props = {}
                required = []
                for param_name, param in sig.parameters.items():
                    if param_name in ["self", "context"]: 
                        continue
                    props[param_name] = {"type": "string"} # Default to string
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)
                
                schema["function"]["parameters"]["properties"] = props
                schema["function"]["parameters"]["required"] = required

            self._schemas[name] = schema
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_definitions(self) -> List[Dict[str, Any]]:
        return list(self._schemas.values())

    def get_all_tools(self) -> Dict[str, Callable]:
        return self._tools

# Global Registry Instance
registry = ToolRegistry()
