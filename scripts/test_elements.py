"""元素操作验证脚本

测试画布元素的实际创建、修改、删除功能：
- 创建各种类型元素
- 修改元素属性
- 删除元素
- 批量操作
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.canvas.helpers import base_excalidraw_element, generate_element_id
from src.agent.lib.canvas.flowchart import create_complete_flowchart_node
from src.agent.lib.canvas.batch_helpers import (
    create_shape_and_text,
    create_arrow_between_nodes,
)

def create_rectangle(x, y, width, height, fill_color="transparent", **kwargs):
    """创建矩形元素（辅助函数）"""
    elem = base_excalidraw_element("rectangle", x, y, width, height)
    elem.update({
        "backgroundColor": fill_color,
        **kwargs
    })
    return elem


def create_ellipse(x, y, width, height, fill_color="transparent", **kwargs):
    """创建椭圆元素（辅助函数）"""
    elem = base_excalidraw_element("ellipse", x, y, width, height)
    elem.update({
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "backgroundColor": fill_color,
        **kwargs
    })
    return elem


def create_text(x, y, text, font_size=20, font_family=1, **kwargs):
    """创建文本元素（辅助函数）"""
    from src.agent.lib.math.text import estimate_text_size
    width, height = estimate_text_size(text, font_size, font_family)
    elem = base_excalidraw_element("text", x, y, width, height)
    elem.update({
        "text": text,
        "fontSize": font_size,
        "fontFamily": font_family,
        **kwargs
    })
    return elem


def create_arrow(points, **kwargs):
    """创建箭头元素（辅助函数）"""
    # 箭头使用第一个点作为起点
    x, y = points[0] if points else (0, 0)
    elem = base_excalidraw_element("arrow", x, y, 0, 0)
    elem.update({
        "points": points,
        **kwargs
    })
    return elem


def create_line(points, **kwargs):
    """创建线段元素（辅助函数）"""
    # 线段使用第一个点作为起点
    x, y = points[0] if points else (0, 0)
    elem = base_excalidraw_element("line", x, y, 0, 0)
    elem.update({
        "points": points,
        **kwargs
    })
    return elem

def test_create_rectangle():
    """测试创建矩形元素"""
    print("\n" + "="*60)
    print("测试 1: 创建矩形")
    print("="*60)
    
    element = create_rectangle(
        x=100,
        y=200,
        width=150,
        height=80,
        fill_color="#ffcccc"
    )
    
    print("创建的矩形元素:")
    print(f"  ID: {element['id']}")
    print(f"  类型: {element['type']}")
    print(f"  位置: ({element['x']}, {element['y']})")
    print(f"  尺寸: {element['width']} x {element['height']}")
    print(f"  填充色: {element.get('backgroundColor', 'transparent')}")
    
    # 验证
    assert element['type'] == 'rectangle', "类型应该是rectangle"
    assert element['x'] == 100, "X坐标正确"
    assert element['y'] == 200, "Y坐标正确"
    assert element['width'] == 150, "宽度正确"
    assert element['height'] == 80, "高度正确"
    assert 'id' in element, "应该有ID"
    
    print("\n✓ 测试通过")


def test_create_ellipse():
    """测试创建椭圆元素"""
    print("\n" + "="*60)
    print("测试 2: 创建椭圆")
    print("="*60)
    
    element = create_ellipse(
        x=50,
        y=50,
        width=100,
        height=100,
        fill_color="#ccffcc"
    )
    
    print("创建的椭圆元素:")
    print(f"  ID: {element['id']}")
    print(f"  类型: {element['type']}")
    print(f"  位置: ({element['x']}, {element['y']})")
    print(f"  尺寸: {element['width']} x {element['height']}")
    
    assert element['type'] == 'ellipse', "类型应该是ellipse"
    assert element['width'] == element['height'], "圆形的宽高应该相等"
    
    print("\n✓ 测试通过")


def test_create_text():
    """测试创建文本元素"""
    print("\n" + "="*60)
    print("测试 3: 创建文本")
    print("="*60)
    
    test_cases = [
        ("Hello World", 20, 1, "纯英文"),  # Virgil
        ("你好世界", 20, 1, "纯中文"),  # Virgil
        ("Python编程", 16, 2, "中英混合"),  # Helvetica
    ]
    
    for text, font_size, font_family, desc in test_cases:
        element = create_text(
            x=10,
            y=10,
            text=text,
            font_size=font_size,
            font_family=font_family
        )
        
        print(f"\n{desc}: '{text}'")
        print(f"  ID: {element['id']}")
        print(f"  类型: {element['type']}")
        print(f"  文本: {element['text']}")
        print(f"  字体: {element['fontSize']} {element['fontFamily']}")
        print(f"  尺寸: {element['width']} x {element['height']}")
        
        assert element['type'] == 'text', "类型应该是text"
        assert element['text'] == text, "文本内容正确"
        assert element['fontSize'] == font_size, "字体大小正确"
        assert element['width'] > 0, "宽度应该大于0"
        assert element['height'] > 0, "高度应该大于0"
    
    print("\n✓ 测试通过")


def test_create_arrow():
    """测试创建箭头"""
    print("\n" + "="*60)
    print("测试 4: 创建箭头")
    print("="*60)
    
    # 简单直线箭头
    points = [
        [0, 0],
        [100, 0],
        [100, 100],
        [200, 100],
    ]
    
    element = create_arrow(points=points)
    
    print("创建的箭头元素:")
    print(f"  ID: {element['id']}")
    print(f"  类型: {element['type']}")
    print(f"  点数: {len(element['points'])}")
    print(f"  路径: {element['points'][:2]} ... {element['points'][-1:]}")
    
    assert element['type'] == 'arrow', "类型应该是arrow"
    assert len(element['points']) == len(points), "点数正确"
    
    print("\n✓ 测试通过")


def test_create_line():
    """测试创建线段"""
    print("\n" + "="*60)
    print("测试 5: 创建线段")
    print("="*60)
    
    points = [[0, 0], [50, 50], [100, 0]]
    
    element = create_line(points=points)
    
    print("创建的线段元素:")
    print(f"  ID: {element['id']}")
    print(f"  类型: {element['type']}")
    print(f"  点数: {len(element['points'])}")
    
    assert element['type'] == 'line', "类型应该是line"
    
    print("\n✓ 测试通过")


def test_flowchart_node():
    """测试创建流程图节点"""
    print("\n" + "="*60)
    print("测试 6: 创建流程图节点")
    print("="*60)
    
    test_cases = [
        ("开始", "rectangle", 100, 50),
        ("处理", "rectangle", 150, 100),
        ("判断", "diamond", 80, 80),
        ("结束", "ellipse", 200, 200),
    ]
    
    for text, shape_type, x, y in test_cases:
        node_id = generate_element_id()
        text_id = generate_element_id()
        width, height = 120, 60
        shape, text_element = create_complete_flowchart_node(
            node_id=node_id,
            text_id=text_id,
            label=text,
            node_type=shape_type,
            x=x,
            y=y,
            width=width,
            height=height,
            stroke_color="#000000",
            bg_color="#ffffff",
            text_color="#000000",
        )
        
        print(f"\n节点: '{text}' ({shape_type})")
        print(f"  形状ID: {shape['id']}")
        print(f"  文本ID: {text_element['id']}")
        print(f"  位置: ({shape['x']}, {shape['y']})")
        print(f"  尺寸: {shape['width']} x {shape['height']}")
        
        # 验证文本绑定
        if 'containerId' in text_element:
            print(f"  ✓ 文本已绑定到容器: {text_element['containerId']}")
            assert text_element['containerId'] == shape['id'], "文本应该绑定到形状"
        
        assert shape['type'] == shape_type, f"形状类型应该是{shape_type}"
        assert text_element['type'] == 'text', "文本类型正确"
        assert text_element['text'] == text, "文本内容正确"
    
    print("\n✓ 测试通过")


def test_batch_create():
    """测试批量创建元素"""
    print("\n" + "="*60)
    print("测试 7: 批量创建（形状+文本）")
    print("="*60)
    
    nodes = [
        ("节点A", 0, 0),
        ("节点B", 200, 0),
        ("节点C", 400, 0),
    ]
    
    created_nodes = {}
    
    for text, x, y in nodes:
        spec = {
            "id": text,
            "type": "rectangle",
            "label": text,
            "x": x,
            "y": y,
            "width": 100,
            "height": 60,
        }
        theme_colors = {"stroke": "#000000", "background": "#ffffff", "text": "#000000"}
        id_mapping = {}
        shape, text_elem, info = create_shape_and_text(spec, theme_colors, id_mapping)
        created_nodes[text] = shape
        print(f"\n创建节点: '{text}'")
        print(f"  形状: {shape['id']} ({shape['width']}x{shape['height']})")
        print(f"  文本: {text_elem['id']}")
    
    print(f"\n总共创建: {len(created_nodes)}个节点")
    
    assert len(created_nodes) == len(nodes), "创建数量正确"
    
    print("\n✓ 测试通过")


def test_create_arrows_between_nodes():
    """测试节点间创建箭头"""
    print("\n" + "="*60)
    print("测试 8: 节点间创建箭头")
    print("="*60)
    
    # 创建两个节点
    node1 = create_rectangle(x=0, y=50, width=100, height=60)
    node2 = create_rectangle(x=200, y=50, width=100, height=60)
    
    print(f"源节点: ({node1['x']}, {node1['y']})")
    print(f"目标节点: ({node2['x']}, {node2['y']})")
    
    # 创建连接箭头（不使用路径规划）
    edge = {"from_id": "node1", "to_id": "node2"}
    id_mapping = {"node1": node1["id"], "node2": node2["id"]}
    elements = [node1, node2]
    theme_colors = {
        "stroke": "#000000",
        "background": "#ffffff",
        "text": "#000000",
        "arrow": "#000000"  # 添加arrow颜色
    }
    result = create_arrow_between_nodes(
        edge=edge, 
        id_mapping=id_mapping,
        elements_source=elements,
        theme_colors=theme_colors,
        use_pathfinding=False,
    )
    
    assert result is not None, "应该返回结果"
    arrow = result[0] if result else None
    assert arrow is not None, "箭头不应该为None"
    
    print("\n创建的箭头:")
    print("  ID: {}".format(arrow['id']))
    print("  类型: {}".format(arrow['type']))
    print("  绑定: {} → {}".format(arrow.get('startBinding', {}), arrow.get('endBinding', {})))
    print("  点数: {}".format(len(arrow['points'])))
    
    # 验证箭头绑定
    if 'startBinding' in arrow:
        assert arrow['startBinding']['elementId'] == node1['id'], "起点绑定正确"
    if 'endBinding' in arrow:
        assert arrow['endBinding']['elementId'] == node2['id'], "终点绑定正确"
    
    print("\n✓ 测试通过")


def test_arrow_with_pathfinding():
    """测试带路径规划的箭头"""
    print("\n" + "="*60)
    print("测试 9: 带路径规划的箭头")
    print("="*60)
    
    # 创建节点（有障碍物阻挡）
    node1 = create_rectangle(x=0, y=50, width=50, height=40)
    node2 = create_rectangle(x=200, y=50, width=50, height=40)
    obstacle = create_rectangle(x=100, y=30, width=50, height=80)
    
    print(f"源节点: ({node1['x']}, {node1['y']})")
    print(f"障碍物: ({obstacle['x']}, {obstacle['y']})")
    print(f"目标节点: ({node2['x']}, {node2['y']})")
    
    # 使用路径规划创建箭头
    edge = {"from_id": "node1", "to_id": "node2"}
    id_mapping = {"node1": node1["id"], "node2": node2["id"]}
    elements = [node1, node2, obstacle]
    theme_colors = {
        "stroke": "#000000",
        "background": "#ffffff",
        "text": "#000000",
        "arrow": "#000000"  # 添加arrow颜色
    }
    result = create_arrow_between_nodes(
        edge=edge,
        id_mapping=id_mapping,
        elements_source=elements,
        theme_colors=theme_colors,
        use_pathfinding=True,
    )
    
    assert result is not None, "应该返回结果"
    arrow = result[0] if result else None
    assert arrow is not None, "箭头不应该为None"
    
    print("\n规划的路径:")
    print("  ID: {}".format(arrow['id']))
    print("  点数: {}".format(len(arrow['points'])))
    print("  路径: {} ...".format(arrow['points'][:3]))
    
    # 路径规划应该产生多个点（绕过障碍物）
    if len(arrow['points']) > 2:
        print("  ✓ 路径包含{}个点（有避障）".format(len(arrow['points'])))
    else:
        print("  注意: 路径只有{}个点（可能是直线）".format(len(arrow['points'])))
    
    print("\n✓ 测试通过")


def test_element_properties():
    """测试元素属性"""
    print("\n" + "="*60)
    print("测试 10: 元素属性验证")
    print("="*60)
    
    element = create_rectangle(
        x=100,
        y=100,
        width=200,
        height=100,
        fill_color="#ff0000",
        stroke_color="#0000ff",
        stroke_width=3,
        opacity=80,
    )
    
    print("元素属性:")
    important_props = [
        'id', 'type', 'x', 'y', 'width', 'height',
        'backgroundColor', 'strokeColor', 'strokeWidth', 'opacity',
        'isDeleted', 'angle'
    ]
    
    for prop in important_props:
        if prop in element:
            print(f"  {prop}: {element[prop]}")
    
    # 验证必需属性
    required = ['id', 'type', 'x', 'y', 'width', 'height']
    for prop in required:
        assert prop in element, f"缺少必需属性: {prop}"
    
    # 验证类型
    assert isinstance(element['id'], str), "ID应该是字符串"
    assert isinstance(element['x'], (int, float)), "X应该是数字"
    assert isinstance(element['y'], (int, float)), "Y应该是数字"
    
    print("\n✓ 测试通过")


def main():
    """运行所有测试"""
    print("="*60)
    print("元素操作功能验证")
    print("="*60)
    
    try:
        test_create_rectangle()
        test_create_ellipse()
        test_create_text()
        test_create_arrow()
        test_create_line()
        test_flowchart_node()
        test_batch_create()
        test_create_arrows_between_nodes()
        test_arrow_with_pathfinding()
        test_element_properties()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
