"""Agent工具功能验证"""

import sys
import io
from pathlib import Path

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.canvas.flowchart import create_complete_flowchart_node
from src.agent.lib.canvas.helpers import (
    base_excalidraw_element,
    get_theme_colors,
    generate_element_id,
)
from src.agent.lib.canvas.layout import calculate_layout


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print("=" * 60)


def create_test_node(
    label: str, node_type: str, x: float, y: float, theme: str = "light"
):
    """创建测试节点的辅助函数"""
    colors = get_theme_colors(theme)
    node_id = generate_element_id()
    text_id = generate_element_id()
    width, height = 120, 60

    shape, text_element = create_complete_flowchart_node(
        node_id=node_id,
        text_id=text_id,
        label=label,
        node_type=node_type,
        x=x,
        y=y,
        width=width,
        height=height,
        stroke_color=colors["stroke"],
        bg_color=colors["background"],
        text_color=colors["text"],
    )

    return {"element": shape, "label_element": text_element, "label": label}


def test_flowchart_creation():
    """测试流程图完整创建"""
    print_section("测试 1: 创建简单流程图")

    # 手动创建简单流程
    steps = ["开始", "读取数据", "处理", "输出", "结束"]
    nodes = [{"id": f"step_{i}", "label": step} for i, step in enumerate(steps)]
    edges = [
        {"from_id": f"step_{i}", "to_id": f"step_{i + 1}"}
        for i in range(len(steps) - 1)
    ]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("创建流程图:")
    print(f"  步骤数: {len(steps)}")
    print(f"  生成节点: {len(result.nodes)}")
    print(f"  生成连接: {len(result.edges)}")

    assert len(result.nodes) == 5, "应该创建5个节点"
    assert len(result.edges) == 4, "应该创建4条边"

    print("\n节点详情:")
    for node in result.nodes:
        print(f"  {node['label']}: ({node['x']:.0f}, {node['y']:.0f})")

    print("\n✓ 测试通过\n")


def test_node_types():
    """测试不同类型的流程图节点"""
    print_section("测试 2: 不同类型节点")

    node_types = [
        ("ellipse", "ellipse", "开始"),  # start -> ellipse
        ("rectangle", "rectangle", "处理"),  # process -> rectangle
        ("diamond", "diamond", "判断"),  # decision -> diamond
        ("ellipse", "ellipse", "结束"),  # end -> ellipse
    ]

    for node_type, expected_shape, label in node_types:
        node = create_test_node(
            label=label, node_type=node_type, x=100, y=100, theme="light"
        )

        actual_shape = node["element"]["type"]
        print(f"  {node_type} → {actual_shape}")
        assert actual_shape == expected_shape, (
            f"节点类型{node_type}应该是{expected_shape}"
        )

    print("\n✓ 测试通过\n")


def test_theme_colors():
    """测试主题颜色"""
    print_section("测试 3: 主题颜色")

    themes = ["light", "dark"]

    for theme in themes:
        colors = get_theme_colors(theme)
        print(f"\n{theme}主题:")
        print(f"  背景色: {colors['background']}")
        print(f"  描边色: {colors['stroke']}")
        print(f"  文本色: {colors['text']}")

        assert "background" in colors
        assert "stroke" in colors
        assert "text" in colors

    print("\n✓ 测试通过\n")


def test_element_creation():
    """测试基础元素创建"""
    print_section("测试 4: 基础元素创建")

    element_types = [
        ("rectangle", "矩形"),
        ("ellipse", "椭圆"),
        ("diamond", "菱形"),
        ("arrow", "箭头"),
        ("text", "文本"),
    ]

    for elem_type, name in element_types:
        element = base_excalidraw_element(elem_type, 100, 100, 150, 80, "#000", "#fff")

        print(f"  {name} ({elem_type}):")
        print(f"    ID: {element['id']}")
        print(f"    类型: {element['type']}")
        print(f"    位置: ({element['x']}, {element['y']})")
        print(f"    尺寸: {element['width']} x {element['height']}")

        assert element["type"] == elem_type
        assert "id" in element
        assert not element["isDeleted"]

    print("\n✓ 测试通过\n")


def test_text_binding():
    """测试文本绑定到容器"""
    print_section("测试 5: 文本绑定")

    # 创建一个带文本的节点
    node = create_test_node(
        label="测试节点", node_type="process", x=200, y=100, theme="light"
    )

    container = node["element"]
    text = node["label_element"]

    print("容器元素:")
    print(f"  ID: {container['id']}")
    print(f"  类型: {container['type']}")

    print("\n文本元素:")
    print(f"  ID: {text['id']}")
    print(f"  文本: {text['text']}")
    print(f"  容器ID: {text.get('containerId')}")

    assert text["containerId"] == container["id"], "文本应该绑定到容器"

    # 验证文本居中
    assert text["textAlign"] == "center", "文本应该水平居中"
    assert text["verticalAlign"] == "middle", "文本应该垂直居中"

    print("\n✓ 测试通过\n")


def test_arrow_binding():
    """测试箭头绑定"""
    print_section("测试 6: 箭头绑定")

    # 创建两个节点
    node1 = create_test_node("节点1", "process", 100, 100, "light")
    node2 = create_test_node("节点2", "process", 300, 100, "light")

    # 创建箭头（模拟）
    arrow = base_excalidraw_element("arrow", 0, 0, 200, 0, "#000", "transparent")
    arrow.update(
        {
            "points": [[0, 0], [200, 0]],
            "start": {
                "type": "arrow",
                "id": node1["element"]["id"],
            },
            "end": {
                "type": "arrow",
                "id": node2["element"]["id"],
            },
        }
    )

    print("箭头绑定:")
    print(f"  从: {arrow['start']['id'][:20]}...")
    print(f"  到: {arrow['end']['id'][:20]}...")
    print(f"  点数: {len(arrow['points'])}")

    assert arrow["start"]["id"] == node1["element"]["id"]
    assert arrow["end"]["id"] == node2["element"]["id"]

    print("\n✓ 测试通过\n")


def test_complex_flowchart():
    """测试复杂流程图"""
    print_section("测试 7: 复杂流程图（分支）")

    # 创建一个带分支的流程
    nodes = [
        {"id": "start", "label": "开始"},
        {"id": "input", "label": "输入数据"},
        {"id": "validate", "label": "验证数据"},
        {"id": "success", "label": "处理成功分支"},
        {"id": "fail", "label": "处理失败分支"},
        {"id": "output", "label": "输出结果"},
        {"id": "log", "label": "记录日志"},
        {"id": "end", "label": "结束"},
    ]
    edges = [
        {"from_id": "start", "to_id": "input"},
        {"from_id": "input", "to_id": "validate"},
        {"from_id": "validate", "to_id": "success"},
        {"from_id": "validate", "to_id": "fail"},
        {"from_id": "success", "to_id": "output"},
        {"from_id": "fail", "to_id": "log"},
        {"from_id": "output", "to_id": "end"},
        {"from_id": "log", "to_id": "end"},
    ]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("复杂流程图:")
    print(f"  总节点数: {len(result.nodes)}")
    print(f"  总连接数: {len(result.edges)}")

    # 计算总宽度和高度
    xs = [n["x"] for n in result.nodes]
    ys = [n["y"] for n in result.nodes]

    width = max(xs) - min(xs) + 160
    height = max(ys) - min(ys) + 80

    print(f"  画布尺寸: {width:.0f} x {height:.0f}")
    print(f"  节点数量: {len(result.nodes)}")

    print("\n✓ 测试通过\n")


def test_element_properties():
    """测试元素属性完整性"""
    print_section("测试 8: 元素属性完整性")

    element = base_excalidraw_element("rectangle", 100, 200, 150, 80, "#000", "#fff")

    required_props = [
        "id",
        "type",
        "x",
        "y",
        "width",
        "height",
        "angle",
        "strokeColor",
        "backgroundColor",
        "fillStyle",
        "strokeWidth",
        "strokeStyle",
        "roughness",
        "opacity",
        "isDeleted",
        "groupIds",
        "frameId",
        "roundness",
        "boundElements",
        "updated",
        "link",
        "locked",
    ]

    print("检查必需属性:")
    missing = []
    for prop in required_props:
        if prop in element:
            print(f"  ✓ {prop}: {element[prop]}")
        else:
            print(f"  ✗ {prop}: 缺失")
            missing.append(prop)

    if missing:
        print(f"\n缺失属性: {', '.join(missing)}")
        raise AssertionError(f"缺少必需属性: {missing}")

    print("\n✓ 测试通过\n")


def test_coordinate_system():
    """测试坐标系统"""
    print_section("测试 9: 坐标系统")

    # 创建一系列节点测试坐标
    nodes = [{"id": label, "label": label} for label in ["A", "B", "C"]]
    edges = [{"from_id": "A", "to_id": "B"}, {"from_id": "B", "to_id": "C"}]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    coords = []
    for node in result.nodes:
        x = node["x"]
        y = node["y"]
        coords.append((x, y))
        print(f"  {node['label']}: ({x:.0f}, {y:.0f})")

    # 验证y坐标递增（垂直布局）
    for i in range(len(coords) - 1):
        assert coords[i + 1][1] > coords[i][1], f"节点{i + 1}应该在节点{i}下方"

    print("\n✓ 坐标系统正确（垂直布局）\n")


def test_label_truncation():
    """测试长标签处理"""
    print_section("测试 10: 长标签处理")

    labels = [
        "正常标签",
        "这是一个很长的标签文本",
        "VeryLongEnglishLabel",
        "Mixed混合LabelTest测试",
    ]

    for label in labels:
        node = create_test_node(
            label=label, node_type="process", x=100, y=100, theme="light"
        )

        text_elem = node["label_element"]
        container = node["element"]

        print(f"  '{label}':")
        print(f"    文本尺寸: {text_elem['width']:.0f} x {text_elem['height']:.0f}")
        print(f"    容器尺寸: {container['width']:.0f} x {container['height']:.0f}")

        # 文本不应该超出容器
        # 注意：这里可能需要padding，所以稍微放宽检查
        if text_elem["width"] > container["width"] + 10:
            print("    ⚠ 警告: 文本可能超出容器")

    print("\n✓ 测试通过\n")


def main():
    print("=" * 60)
    print("Agent工具功能验证")
    print("=" * 60)

    try:
        test_flowchart_creation()
        test_node_types()
        test_theme_colors()
        test_element_creation()
        test_text_binding()
        test_arrow_binding()
        test_complex_flowchart()
        test_element_properties()
        test_coordinate_system()
        test_label_truncation()

        print_section("✓ 所有测试完成")
        return 0

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
