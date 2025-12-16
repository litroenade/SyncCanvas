"""模块名称: schemas
主要功能: Excalidraw 工具参数 Schema 定义
"""

from typing import Optional, List, Literal, Dict, Any

from pydantic import BaseModel, Field

ExcalidrawShapeType = Literal["rectangle", "diamond", "ellipse", "text"]
ComponentType = Literal["service", "database", "module", "client"]

class CreateFlowchartNodeArgs(BaseModel):
    """创建流程图节点的参数

    Attributes:
        label: 节点内部的文字标签
        node_type: 节点类型
        x: 画布上的 X 坐标
        y: 画布上的 Y 坐标
        width: 节点宽度
        height: 节点高度
        stroke_color: 描边颜色
        bg_color: 背景颜色
    """

    label: str = Field(..., description="节点内部的文字标签")
    node_type: ExcalidrawShapeType = Field(
        "rectangle",
        description="节点类型: rectangle(流程步骤), diamond(判断), ellipse(开始/结束)",
    )
    x: float = Field(..., description="画布上的 X 坐标")
    y: float = Field(..., description="画布上的 Y 坐标")
    width: float = Field(160.0, description="节点宽度")
    height: float = Field(70.0, description="节点高度")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("#ffffff", description="背景颜色")


class ConnectNodesArgs(BaseModel):
    """连接两个节点的参数

    Attributes:
        from_id: 起始节点的 ID
        to_id: 结束节点的 ID
        label: 连线上的文字标签
        stroke_color: 连线颜色
    """

    from_id: str = Field(
        ..., description="起始节点的 ID (create_flowchart_node 返回的 element_id)"
    )
    to_id: str = Field(
        ..., description="结束节点的 ID (create_flowchart_node 返回的 element_id)"
    )
    label: Optional[str] = Field(None, description="连线上的文字标签 (如 '是', '否')")
    stroke_color: str = Field("#1e1e1e", description="连线颜色")

class CreateExcalidrawElementArgs(BaseModel):
    """创建 Excalidraw 元素的参数

    Attributes:
        element_type: 元素类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        text: 文本内容
        stroke_color: 描边颜色
        bg_color: 背景颜色
    """

    element_type: str = Field(
        ..., description="元素类型: rectangle, diamond, ellipse, arrow, line, text"
    )
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(100.0, description="宽度")
    height: float = Field(100.0, description="高度")
    text: str = Field("", description="文本内容 (仅 text 类型需要)")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("transparent", description="背景颜色")


class ListElementsArgs(BaseModel):
    """列出元素的参数

    Attributes:
        limit: 返回的元素数量上限
    """

    limit: int = Field(30, description="返回的元素数量上限")


class GetCanvasBoundsArgs(BaseModel):
    """获取画布边界的参数

    无需额外参数，仅依赖 context 中的 session_id。
    """


class UpdateElementArgs(BaseModel):
    """更新元素的参数

    Attributes:
        element_id: 元素 ID
        x: 新的 X 坐标
        y: 新的 Y 坐标
        width: 新的宽度
        height: 新的高度
        text: 新的文本内容
        stroke_color: 新的描边颜色
        bg_color: 新的背景颜色
    """

    element_id: str = Field(..., description="元素 ID")
    x: Optional[float] = Field(None, description="新的 X 坐标")
    y: Optional[float] = Field(None, description="新的 Y 坐标")
    width: Optional[float] = Field(None, description="新的宽度")
    height: Optional[float] = Field(None, description="新的高度")
    text: Optional[str] = Field(None, description="新的文本内容")
    stroke_color: Optional[str] = Field(None, description="新的描边颜色")
    bg_color: Optional[str] = Field(None, description="新的背景颜色")


class DeleteElementsArgs(BaseModel):
    """删除元素的参数

    Attributes:
        element_ids: 要删除的元素 ID 列表
    """

    element_ids: List[str] = Field(..., description="要删除的元素 ID 列表")


class ClearCanvasArgs(BaseModel):
    """清空画布的参数

    Attributes:
        confirm: 确认标志
    """

    confirm: bool = Field(True, description="确认标志")


class GetElementByIdArgs(BaseModel):
    """获取元素详情的参数

    Attributes:
        element_id: 元素 ID
    """

    element_id: str = Field(..., description="要查询的元素 ID")


class CreateContainerArgs(BaseModel):
    """创建容器的参数

    Attributes:
        title: 容器标题
        x: 左上角 X 坐标
        y: 左上角 Y 坐标
        width: 容器宽度
        height: 容器高度
        stroke_color: 边框颜色
        bg_color: 背景颜色
        title_color: 标题文字颜色
    """

    title: str = Field(..., description="容器标题 (如 '前端', '后端', '数据库层')")
    x: float = Field(..., description="左上角 X 坐标")
    y: float = Field(..., description="左上角 Y 坐标")
    width: float = Field(300, description="容器宽度")
    height: float = Field(400, description="容器高度")
    stroke_color: str = Field("#a1a1aa", description="边框颜色")
    bg_color: str = Field("#fafafa", description="背景颜色")
    title_color: str = Field("#71717a", description="标题文字颜色")


class CreateComponentArgs(BaseModel):
    """创建组件的参数

    Attributes:
        label: 组件标签
        component_type: 组件类型
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 边框颜色
        bg_color: 背景颜色
    """

    label: str = Field(..., description="组件标签")
    component_type: ComponentType = Field(
        "service",
        description="组件类型: service(服务), database(数据库), module(模块), client(客户端)",
    )
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(150, description="宽度")
    height: float = Field(50, description="高度")
    stroke_color: str = Field("#6b7280", description="边框颜色")
    bg_color: str = Field("#f3f4f6", description="背景颜色")

class CreatePresetElementArgs(BaseModel):
    """使用预设创建元素的参数

    Attributes:
        preset: 预设名称
        label: 元素标签文字
        x: X 坐标
        y: Y 坐标
    """

    preset: str = Field(
        ...,
        description="预设名称: flowchart_start, flowchart_end, flowchart_process, flowchart_decision, flowchart_io",
    )
    label: str = Field(..., description="元素标签文字")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")


class BatchUpdateArgs(BaseModel):
    """批量更新元素的参数

    Attributes:
        updates: 更新列表，每项包含 id 和要更新的属性
    """

    updates: List[Dict[str, Any]] = Field(
        ..., description="更新列表，每项包含 id 和要更新的属性"
    )


class ElementSpec(BaseModel):
    """单个元素规格描述

    Attributes:
        id: 临时 ID (用于边关联)
        type: 元素类型
        label: 标签文字
        x: X 坐标
        y: Y 坐标
        width: 宽度
        height: 高度
        stroke_color: 描边颜色
        bg_color: 背景颜色
    """

    id: str = Field(..., description="临时 ID (用于边关联，如 'n1', 'n2')")
    type: str = Field(
        "rectangle",
        description="元素类型: rectangle, diamond, ellipse, text",
    )
    label: str = Field(..., description="标签文字")
    x: float = Field(..., description="X 坐标")
    y: float = Field(..., description="Y 坐标")
    width: float = Field(160, description="宽度")
    height: float = Field(70, description="高度")
    stroke_color: str = Field("#1e1e1e", description="描边颜色")
    bg_color: str = Field("#ffffff", description="背景颜色")


class EdgeSpec(BaseModel):
    """边 (连接线) 规格描述

    Attributes:
        from_id: 起始元素临时 ID
        to_id: 结束元素临时 ID
        label: 边标签 (可选)
    """

    from_id: str = Field(..., description="起始元素临时 ID (如 'n1')")
    to_id: str = Field(..., description="结束元素临时 ID (如 'n2')")
    label: Optional[str] = Field(None, description="边标签 (可选，如 '是', '否')")


class BatchCreateElementsArgs(BaseModel):
    """批量创建元素的参数 (支持 LLM 返回的 JSON 规划)

    Attributes:
        elements: 元素规格列表
        edges: 边 (连接线) 规格列表
    """

    elements: List[ElementSpec] = Field(..., description="元素规格列表")
    edges: List[EdgeSpec] = Field(
        default_factory=list, description="边 (连接线) 规格列表"
    )
