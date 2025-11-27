"""模块名称: agent
主要功能: AI 智能体，根据用户提示词生成白板图形
"""

import uuid
from typing import List, Dict, Any

import json_repair
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from src.logger import get_logger

logger = get_logger(__name__)


class AIShape(BaseModel):
    """AI 生成的图形模型"""

    type: str = Field(..., description="图形类型: rect, circle, text")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(100, description="宽度")
    height: float = Field(100, description="高度")
    text: str = Field("", description="文本内容")
    fill: str = Field("#E0E0E0", description="填充颜色")
    strokeColor: str = Field("#000000", description="描边颜色")


class AIAgent:
    """AI 智能体"""

    def __init__(self):
        """初始化 AI 智能体"""
        if not OPENAI_API_KEY:
            logger.warning("未配置 OPENAI_API_KEY，AI 功能将不可用")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.model = OPENAI_MODEL

    async def generate_shapes(self, prompt: str) -> List[Dict[str, Any]]:
        """根据提示词生成图形列表

        Args:
            prompt: 用户输入的提示词

        Returns:
            List[Dict[str, Any]]: 图形数据列表
        """
        if not self.client:
            logger.error("AI 客户端未初始化")
            raise ValueError("AI 服务未配置")

        system_prompt = """You are a professional UI/UX designer and drawing engine.
Please generate a set of graphic data based on the user's description.
Do not explain, just return a JSON array.
Coordinate system: x axis to the right, y axis down.

Available types (type):
- rect: rectangle, used for containers, buttons, cards
- circle: circle, used for avatars, icons
- text: text, used for titles, labels
- arrow: arrow, used for connecting nodes
- line: line, used for splitting

Layout rules:
1. Automatically calculate coordinates (x, y), avoid overlapping graphics.
2. Maintain reasonable spacing (padding/margin).
3. For flowcharts, use arrows to connect related nodes.
4. Container should contain its internal elements.

Default properties:
- width/height: default 100
- fill: default #E0E0E0 (light gray)
- strokeColor: default #000000 (black)

Example output:
[
  {"type": "rect", "x": 100, "y": 100, "width": 300, "height": 200, "fill": "#FFFFFF", "strokeColor": "#333333"},
  {"type": "text", "x": 120, "y": 120, "text": "Login", "fill": "#333333"},
  {"type": "arrow", "x": 410, "y": 200, "width": 50, "height": 10, "fill": "#000000"}
]
"""

        try:
            logger.info("正在调用 AI 生成图形: %s", prompt)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            logger.debug("AI 原始响应: %s", content)

            # 使用 json_repair 修复可能的 JSON 格式错误
            clean_json = json_repair.loads(content)

            valid_shapes = []
            if isinstance(clean_json, list):
                for item in clean_json:
                    try:
                        # 验证并转换数据
                        shape = AIShape(**item)
                        shape_dict = shape.model_dump()
                        # 生成唯一 ID
                        shape_dict["id"] = str(uuid.uuid4())
                        valid_shapes.append(shape_dict)
                    except ValidationError as e:
                        logger.warning("跳过无效图形数据: %s, 错误: %s", item, e)

            logger.info("成功生成 %d 个图形", len(valid_shapes))
            return valid_shapes

        except Exception as e:
            logger.error("AI 生成失败: %s", e, exc_info=True)
            raise


# 全局实例
ai_agent = AIAgent()
