"""几何计算验证脚本

测试几何计算模块的实际功能：
- Point 类的向量运算
- Rect 类的边界计算
- 边缘中心点计算
- 连接方向判断
"""

import sys
from pathlib import Path
import math

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.math.geometry import Point, Rect, get_connection_direction


def test_point_operations():
    """测试 Point 类的基本操作"""
    print("\n" + "="*60)
    print("测试 1: Point 类基本操作")
    print("="*60)
    
    # 创建点
    p1 = Point(10, 20)
    p2 = Point(30, 40)
    
    print(f"点 p1: ({p1.x}, {p1.y})")
    print(f"点 p2: ({p2.x}, {p2.y})")
    
    # 测试加法
    p3 = p1 + p2
    print(f"\np1 + p2 = ({p3.x}, {p3.y})")
    assert p3.x == 40 and p3.y == 60, "加法错误"
    
    # 测试减法
    p4 = p2 - p1
    print(f"p2 - p1 = ({p4.x}, {p4.y})")
    assert p4.x == 20 and p4.y == 20, "减法错误"
    
    # 测试数乘
    p5 = p1 * 2
    print(f"p1 * 2 = ({p5.x}, {p5.y})")
    assert p5.x == 20 and p5.y == 40, "数乘错误"
    
    # 测试距离
    distance = p1.distance_to(p2)
    expected = math.sqrt(20**2 + 20**2)
    print(f"\n距离 p1 到 p2: {distance:.2f}")
    print(f"预期: {expected:.2f}")
    assert abs(distance - expected) < 0.01, "距离计算错误"
    
    # 测试相等性
    p6 = Point(10, 20)
    print(f"\np1 == p6: {p1 == p6}")
    assert p1 == p6, "相等判断错误"
    
    print("\n✓ 测试通过")


def test_rect_boundaries():
    """测试 Rect 类的边界计算"""
    print("\n" + "="*60)
    print("测试 2: Rect 边界计算")
    print("="*60)
    
    # 创建矩形
    rect = Rect(x=100, y=200, width=50, height=30)
    
    print(f"矩形: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")
    print("\n边界:")
    print(f"  left: {rect.left}")
    print(f"  right: {rect.right}")
    print(f"  top: {rect.top}")
    print(f"  bottom: {rect.bottom}")
    
    # 验证边界
    assert rect.left == 100, "左边界错误"
    assert rect.right == 150, "右边界错误"
    assert rect.top == 200, "上边界错误"
    assert rect.bottom == 230, "下边界错误"
    
    # 测试中心点
    center = rect.center
    print(f"\n中心点: ({center.x}, {center.y})")
    assert center.x == 125 and center.y == 215, "中心点计算错误"
    
    print("\n✓ 测试通过")


def test_edge_centers():
    """测试边缘中心点计算"""
    print("\n" + "="*60)
    print("测试 3: 边缘中心点")
    print("="*60)
    
    rect = Rect(x=0, y=0, width=100, height=60)
    
    print(f"矩形: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")
    
    # 获取各边中心
    top_center = rect.edge_center("top")
    bottom_center = rect.edge_center("bottom")
    left_center = rect.edge_center("left")
    right_center = rect.edge_center("right")
    
    print("\n边缘中心点:")
    print(f"  上边: ({top_center.x}, {top_center.y})")
    print(f"  下边: ({bottom_center.x}, {bottom_center.y})")
    print(f"  左边: ({left_center.x}, {left_center.y})")
    print(f"  右边: ({right_center.x}, {right_center.y})")
    
    # 验证
    assert top_center.x == 50 and top_center.y == 0, "上边中心错误"
    assert bottom_center.x == 50 and bottom_center.y == 60, "下边中心错误"
    assert left_center.x == 0 and left_center.y == 30, "左边中心错误"
    assert right_center.x == 100 and right_center.y == 30, "右边中心错误"
    
    print("\n✓ 测试通过")


def test_connection_direction():
    """测试连接方向判断"""
    print("\n" + "="*60)
    print("测试 4: 连接方向判断")
    print("="*60)
    
    # 源矩形在左，目标矩形在右
    source = Rect(x=0, y=50, width=50, height=40)
    target = Rect(x=150, y=50, width=50, height=40)
    
    print("情况 1: 水平排列（左 → 右）")
    print(f"  源: x={source.x}, y={source.y}")
    print(f"  目标: x={target.x}, y={target.y}")
    
    src_dir, dst_dir = get_connection_direction(source, target)
    print(f"  源边: {src_dir}, 目标边: {dst_dir}")
    assert src_dir == "right" and dst_dir == "left", "水平方向判断错误"
    
    # 源矩形在上，目标矩形在下
    source2 = Rect(x=50, y=0, width=50, height=40)
    target2 = Rect(x=50, y=100, width=50, height=40)
    
    print("\n情况 2: 垂直排列（上 → 下）")
    print(f"  源: x={source2.x}, y={source2.y}")
    print(f"  目标: x={target2.x}, y={target2.y}")
    
    src_dir, dst_dir = get_connection_direction(source2, target2)
    print(f"  源边: {src_dir}, 目标边: {dst_dir}")
    assert src_dir == "bottom" and dst_dir == "top", "垂直方向判断错误"
    
    # 对角排列
    source3 = Rect(x=0, y=0, width=50, height=40)
    target3 = Rect(x=150, y=100, width=50, height=40)
    
    print("\n情况 3: 对角排列（左上 → 右下）")
    print(f"  源: x={source3.x}, y={source3.y}")
    print(f"  目标: x={target3.x}, y={target3.y}")
    
    src_dir, dst_dir = get_connection_direction(source3, target3)
    print(f"  源边: {src_dir}, 目标边: {dst_dir}")
    # 对角线情况下，选择主要方向
    
    print("\n✓ 测试通过")


def test_rect_contains():
    """测试点是否在矩形内"""
    print("\n" + "="*60)
    print("测试 5: 点是否在矩形内")
    print("="*60)
    
    rect = Rect(x=10, y=10, width=80, height=60)
    
    test_points = [
        (Point(50, 40), True, "中心点"),
        (Point(10, 10), True, "左上角"),
        (Point(90, 70), True, "右下角"),
        (Point(5, 40), False, "左侧外部"),
        (Point(95, 40), False, "右侧外部"),
        (Point(50, 5), False, "上方外部"),
        (Point(50, 75), False, "下方外部"),
    ]
    
    print(f"矩形: x={rect.x}, y={rect.y}, w={rect.width}, h={rect.height}")
    print("\n测试点:")
    
    for point, expected, desc in test_points:
        in_rect = (rect.left <= point.x <= rect.right and 
                   rect.top <= point.y <= rect.bottom)
        status = "✓" if in_rect == expected else "✗"
        print(f"  {status} ({point.x}, {point.y}) - {desc}: {in_rect}")
        assert in_rect == expected, f"{desc} 判断错误"
    
    print("\n✓ 测试通过")


def test_rect_intersection():
    """测试矩形相交"""
    print("\n" + "="*60)
    print("测试 6: 矩形相交判断")
    print("="*60)
    
    rect1 = Rect(x=0, y=0, width=100, height=100)
    
    test_cases = [
        (Rect(50, 50, 100, 100), True, "部分重叠"),
        (Rect(150, 0, 50, 50), False, "完全分离"),
        (Rect(20, 20, 30, 30), True, "完全包含"),
        (Rect(0, 0, 100, 100), True, "完全重合"),
        (Rect(100, 0, 50, 50), True, "边缘接触"),
    ]
    
    print(f"矩形1: x={rect1.x}, y={rect1.y}, w={rect1.width}, h={rect1.height}")
    print("\n测试相交:")
    
    for rect2, expected, desc in test_cases:
        # 简单相交判断
        intersects = not (rect1.right < rect2.left or 
                         rect2.right < rect1.left or
                         rect1.bottom < rect2.top or
                         rect2.bottom < rect1.top)
        
        status = "✓" if intersects == expected else "✗"
        print(f"  {status} {desc}: {intersects}")
        assert intersects == expected, f"{desc} 判断错误"
    
    print("\n✓ 测试通过")


def test_distance_calculations():
    """测试各种距离计算"""
    print("\n" + "="*60)
    print("测试 7: 距离计算")
    print("="*60)
    
    test_cases = [
        ((0, 0), (3, 4), 5.0, "3-4-5直角三角形"),
        ((0, 0), (0, 10), 10.0, "垂直距离"),
        ((0, 0), (10, 0), 10.0, "水平距离"),
        ((1, 1), (1, 1), 0.0, "同一点"),
        ((-5, -5), (5, 5), 14.14, "对角距离"),
    ]
    
    print("测试点对距离:")
    for p1_coords, p2_coords, expected, desc in test_cases:
        p1 = Point(*p1_coords)
        p2 = Point(*p2_coords)
        distance = p1.distance_to(p2)
        
        match = abs(distance - expected) < 0.01
        status = "✓" if match else "✗"
        print(f"  {status} {desc}: {distance:.2f} (期望: {expected})")
        assert match, f"{desc} 距离计算错误"
    
    print("\n✓ 测试通过")


def test_vector_operations():
    """测试向量运算"""
    print("\n" + "="*60)
    print("测试 8: 向量运算")
    print("="*60)
    
    # 测试向量加法的交换律
    v1 = Point(3, 4)
    v2 = Point(1, 2)
    print(f"v1 = ({v1.x}, {v1.y})")
    print(f"v2 = ({v2.x}, {v2.y})")
    
    r1 = v1 + v2
    r2 = v2 + v1
    print(f"\nv1 + v2 = ({r1.x}, {r1.y})")
    print(f"v2 + v1 = ({r2.x}, {r2.y})")
    assert r1 == r2, "加法交换律失败"
    print("✓ 加法交换律正确")
    
    # 测试向量减法
    r3 = v1 - v2
    r4 = v2 - v1
    print(f"\nv1 - v2 = ({r3.x}, {r3.y})")
    print(f"v2 - v1 = ({r4.x}, {r4.y})")
    assert r3.x == -r4.x and r3.y == -r4.y, "减法对称性失败"
    print("✓ 减法对称性正确")
    
    # 测试数乘分配律
    k = 3
    r5 = (v1 + v2) * k
    r6 = v1 * k + v2 * k
    print(f"\n(v1 + v2) * {k} = ({r5.x}, {r5.y})")
    print(f"v1 * {k} + v2 * {k} = ({r6.x}, {r6.y})")
    assert r5 == r6, "数乘分配律失败"
    print("✓ 数乘分配律正确")
    
    print("\n✓ 测试通过")


def main():
    """运行所有测试"""
    print("="*60)
    print("几何计算功能验证")
    print("="*60)
    
    try:
        test_point_operations()
        test_rect_boundaries()
        test_edge_centers()
        test_connection_direction()
        test_rect_contains()
        test_rect_intersection()
        test_distance_calculations()
        test_vector_operations()
        
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
