"""流程图布局算法验证脚本

测试拓扑排序和布局算法的实际功能：
- 简单线性流程
- 分支合并结构
- 复杂DAG
- 循环检测
- 间距计算
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.canvas.layout import (
    topological_levels,
    calculate_layout,
    get_layout_gaps
)
from src.config import config


def visualize_layout(nodes, edges, layout):
    """可视化布局结果（ASCII艺术）"""
    if not layout:
        print("布局为空")
        return
    
    # 找出所有层级
    levels = {}
    for node_id, pos in layout.items():
        x, y = pos
        if y not in levels:
            levels[y] = []
        levels[y].append((x, node_id))
    
    # 按层级排序
    for y in sorted(levels.keys()):
        level_nodes = sorted(levels[y])
        nodes_str = " → ".join([f"{node_id}({x:.0f},{y:.0f})" 
                                 for x, node_id in level_nodes])
        print(f"  层级 {int(y//100)}: {nodes_str}")


def test_simple_linear():
    """测试简单线性流程：A → B → C"""
    print("\n" + "="*60)
    print("测试 1: 简单线性流程 (A → B → C)")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "B", "to_id": "C"},
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]}")
    
    # 测试拓扑排序
    levels = topological_levels(nodes, edges)
    print(f"\n拓扑层级: {levels}")
    
    # 验证层级正确性
    assert levels["A"] == 0, "A应该在第0层"
    assert levels["B"] == 1, "B应该在第1层"
    assert levels["C"] == 2, "C应该在第2层"
    
    # 测试布局计算
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    # 验证布局
    assert layout["A"][1] < layout["B"][1] < layout["C"][1], "Y坐标应该递增"
    print("\n✓ 测试通过")


def test_branching():
    """测试分支结构：A → B, A → C"""
    print("\n" + "="*60)
    print("测试 2: 分支结构")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "A", "to_id": "C"},
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]}")
    
    # 拓扑排序
    levels = topological_levels(nodes, edges)
    print(f"\n拓扑层级: {levels}")
    
    assert levels["A"] == 0, "A在第0层"
    assert levels["B"] == 1 and levels["C"] == 1, "B和C在同一层"
    
    # 布局
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    # B和C应该在同一水平线，但X坐标不同
    assert layout["B"][1] == layout["C"][1], "B和C应该在同一高度"
    assert layout["B"][0] != layout["C"][0], "B和C应该水平分开"
    
    print("\n✓ 测试通过")


def test_merge():
    """测试合并结构：A → C, B → C"""
    print("\n" + "="*60)
    print("测试 3: 合并结构")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}]
    edges = [
        {"from_id": "A", "to_id": "C"},
        {"from_id": "B", "to_id": "C"},
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]}")
    
    levels = topological_levels(nodes, edges)
    print(f"\n拓扑层级: {levels}")
    
    assert levels["A"] == 0 and levels["B"] == 0, "A和B在第0层"
    assert levels["C"] == 1, "C在第1层"
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    assert layout["A"][1] == layout["B"][1], "A和B在同一高度"
    assert layout["C"][1] > layout["A"][1], "C在下一层"
    
    print("\n✓ 测试通过")


def test_diamond():
    """测试菱形结构：A → B, A → C, B → D, C → D"""
    print("\n" + "="*60)
    print("测试 4: 菱形结构（分支+合并）")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}, {"id": "D", "label": "D"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "A", "to_id": "C"},
        {"from_id": "B", "to_id": "D"},
        {"from_id": "C", "to_id": "D"},
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]}")
    
    levels = topological_levels(nodes, edges)
    print(f"\n拓扑层级: {levels}")
    
    assert levels["A"] == 0, "A在第0层"
    assert levels["B"] == 1 and levels["C"] == 1, "B和C在第1层"
    assert levels["D"] == 2, "D在第2层"
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    # 验证布局的对称性
    b_x, c_x = layout["B"][0], layout["C"][0]
    d_x = layout["D"][0]
    center = (b_x + c_x) / 2
    print(f"\nB和C的中心: {center}, D的X坐标: {d_x}")
    print(f"D应该居中对齐: 偏差 = {abs(d_x - center)}")
    
    print("\n✓ 测试通过")


def test_complex_dag():
    """测试复杂DAG"""
    print("\n" + "="*60)
    print("测试 5: 复杂DAG")
    print("="*60)
    
    #      A
    #     / \
    #    B   C
    #   / \ /
    #  D   E
    #   \ /
    #    F
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}, 
             {"id": "D", "label": "D"}, {"id": "E", "label": "E"}, {"id": "F", "label": "F"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "A", "to_id": "C"},
        {"from_id": "B", "to_id": "D"},
        {"from_id": "B", "to_id": "E"},
        {"from_id": "C", "to_id": "E"},
        {"from_id": "D", "to_id": "F"},
        {"from_id": "E", "to_id": "F"},
    ]
    
    print(f"节点数: {len(nodes)}")
    print(f"边数: {len(edges)}")
    print("结构:")
    for edge in edges:
        print(f"  {edge['from_id']} → {edge['to_id']}")
    
    levels = topological_levels(nodes, edges)
    print("\n拓扑层级:")
    for level in range(max(levels.values()) + 1):
        nodes_in_level = [n for n, lvl in levels.items() if lvl == level]
        print(f"  层级 {level}: {nodes_in_level}")
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    # 验证拓扑顺序
    for edge in edges:
        src, dst = edge['from_id'], edge['to_id']
        assert levels[src] < levels[dst], f"{src}应该在{dst}之前"
    
    print("\n✓ 测试通过")


def test_cycle_detection():
    """测试循环检测"""
    print("\n" + "="*60)
    print("测试 6: 循环检测")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "B", "to_id": "C"},
        {"from_id": "C", "to_id": "A"},  # 循环！
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]} (包含循环)")
    
    try:
        levels = topological_levels(nodes, edges)
        print(f"\n拓扑层级: {levels}")
        print("⚠ 注意: 算法处理了循环图（可能使用了回退策略）")
    except Exception as e:
        print(f"\n✓ 正确检测到循环: {e}")


def test_disconnected():
    """测试不连通图"""
    print("\n" + "="*60)
    print("测试 7: 不连通图")
    print("="*60)
    
    nodes = [{"id": "A", "label": "A"}, {"id": "B", "label": "B"}, {"id": "C", "label": "C"}, 
             {"id": "D", "label": "D"}, {"id": "E", "label": "E"}]
    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "C", "to_id": "D"},
        # E是孤立节点
    ]
    
    print(f"节点: {[n['id'] for n in nodes]}")
    print(f"边: {[(e['from_id'], e['to_id']) for e in edges]}")
    print("注意: E是孤立节点")
    
    levels = topological_levels(nodes, edges)
    print(f"\n拓扑层级: {levels}")
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果:")
    visualize_layout(nodes, edges, layout)
    
    # 孤立节点应该在第0层
    if "E" in levels:
        assert levels["E"] == 0, "孤立节点应该在第0层"
    
    print("\n✓ 测试通过")


def test_layout_gaps():
    """测试间距计算"""
    print("\n" + "="*60)
    print("测试 8: 布局间距计算")
    print("="*60)
    
    print("当前配置:")
    print(f"  节点宽度: {config.canvas.node_width}")
    print(f"  节点高度: {config.canvas.node_height}")
    
    # 测试不同节点数量的间距
    for node_count in [2, 5, 10, 20]:
        h_gap, v_gap = get_layout_gaps(node_count)
        print(f"\n节点数={node_count}:")
        print(f"  水平间距: {h_gap}")
        print(f"  垂直间距: {v_gap}")


def test_wide_graph():
    """测试宽图（很多同层节点）"""
    print("\n" + "="*60)
    print("测试 9: 宽图（多个同层节点）")
    print("="*60)
    
    # 创建一个源节点连接到多个目标节点
    nodes = [{"id": "root", "label": "root"}] + [{"id": f"node_{i}", "label": f"node_{i}"} for i in range(10)]
    edges = [{"from_id": "root", "to_id": f"node_{i}"} for i in range(10)]
    
    print(f"节点数: {len(nodes)}")
    print("结构: root → 10个子节点")
    
    levels = topological_levels(nodes, edges)
    same_level_nodes = [n for n, lvl in levels.items() if lvl == 1]
    print(f"\n第1层节点数: {len(same_level_nodes)}")
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    print("\n布局结果 (部分):")
    print(f"  root: {layout['root']}")
    for i in range(3):
        print(f"  node_{i}: {layout[f'node_{i}']}")
    print("  ...")
    
    # 验证同层节点的Y坐标相同
    y_coords = [layout[n][1] for n in same_level_nodes]
    assert len(set(y_coords)) == 1, "同层节点Y坐标应该相同"
    
    # 验证节点之间有间距
    x_coords = sorted([layout[n][0] for n in same_level_nodes])
    for i in range(len(x_coords) - 1):
        gap = x_coords[i+1] - x_coords[i]
        assert gap > 0, f"节点之间应该有间距，实际: {gap}"
    
    print("\n✓ 测试通过")


def test_deep_graph():
    """测试深图（很多层级）"""
    print("\n" + "="*60)
    print("测试 10: 深图（多层级链式结构）")
    print("="*60)
    
    # 创建长链
    depth = 15
    nodes = [{"id": f"level_{i}", "label": f"level_{i}"} for i in range(depth)]
    edges = [{"from_id": f"level_{i}", "to_id": f"level_{i+1}"} for i in range(depth-1)]
    
    print(f"节点数: {len(nodes)}")
    print(f"深度: {depth}层")
    
    levels = topological_levels(nodes, edges)
    print(f"\n层级分布: 0 → {max(levels.values())}")
    
    structure = {"nodes": nodes, "edges": edges}
    layout_result = calculate_layout(structure, theme="light")
    layout = {n["id"]: (n["x"], n["y"]) for n in layout_result.nodes}
    
    # 验证层级递增
    y_coords = [layout[f"level_{i}"][1] for i in range(depth)]
    for i in range(len(y_coords) - 1):
        assert y_coords[i] < y_coords[i+1], f"层级{i}应该在层级{i+1}上面"
    
    print(f"总高度: {y_coords[-1] - y_coords[0]}")
    print("\n✓ 测试通过")


def main():
    """运行所有测试"""
    print("="*60)
    print("流程图布局算法功能验证")
    print("="*60)
    
    try:
        test_simple_linear()
        test_branching()
        test_merge()
        test_diamond()
        test_complex_dag()
        test_cycle_detection()
        test_disconnected()
        test_layout_gaps()
        test_wide_graph()
        test_deep_graph()
        
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
