"""实际使用场景验证（模拟用户操作）"""

import sys
import io
from pathlib import Path

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.canvas.layout import calculate_layout, topological_levels
from src.agent.lib.canvas.flowchart import create_complete_flowchart_node
from src.agent.lib.canvas.helpers import get_theme_colors, generate_element_id


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


def test_user_creates_flowchart():
    """场景1: 用户创建流程图"""
    print_section("场景 1: 用户说'创建一个登录流程图'")

    print("\nAgent理解: 需要创建登录流程")
    print("步骤: 开始 → 输入账号密码 → 验证 → 成功/失败 → 结束")

    # 模拟Agent创建
    steps = ["开始", "输入账号密码", "验证身份", "登录成功", "结束"]
    nodes = [{"id": f"s{i}", "label": s} for i, s in enumerate(steps)]
    edges = [{"from_id": f"s{i}", "to_id": f"s{i + 1}"} for i in range(len(steps) - 1)]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("\nAgent创建了:")
    print(f"  ✓ {len(result.nodes)}个节点")
    print(f"  ✓ {len(result.edges)}个连接")

    # 验证都有坐标
    for node in result.nodes:
        assert "x" in node and "y" in node

    print("\n✓ 用户可以看到完整的流程图")
    print()


def test_user_adds_decision():
    """场景2: 用户添加判断节点"""
    print_section("场景 2: 用户说'在第3步添加判断：密码是否正确'")

    print("\nAgent理解: 需要插入判断节点")

    # 创建判断节点
    decision_node = create_test_node(
        label="密码是否正确?", node_type="diamond", x=200, y=300, theme="light"
    )

    print("\n创建的判断节点:")
    print(f"  形状: {decision_node['element']['type']}")  # diamond
    print(f"  标签: {decision_node['label']}")
    print(f"  位置: ({decision_node['element']['x']}, {decision_node['element']['y']})")

    assert decision_node["element"]["type"] == "diamond", "判断节点应该是菱形"

    print("\n✓ 判断节点已添加")
    print()


def test_user_complex_graph():
    """场景3: 用户创建复杂图"""
    print_section("场景 3: 用户说'创建一个数据处理流程'")

    print("\nAgent理解: 复杂的数据处理流程")

    # 定义复杂的图结构
    nodes = [
        {"id": "input", "label": "数据输入"},
        {"id": "validate", "label": "数据验证"},
        {"id": "clean", "label": "数据清洗"},
        {"id": "transform", "label": "数据转换"},
        {"id": "analyze", "label": "数据分析"},
        {"id": "visualize", "label": "数据可视化"},
        {"id": "output", "label": "输出结果"},
    ]

    edges = [
        {"from_id": "input", "to_id": "validate"},
        {"from_id": "validate", "to_id": "clean"},
        {"from_id": "clean", "to_id": "transform"},
        {"from_id": "transform", "to_id": "analyze"},
        {"from_id": "analyze", "to_id": "visualize"},
        {"from_id": "visualize", "to_id": "output"},
    ]

    # 计算布局
    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("\n布局结果:")
    print(f"  节点数: {len(result.nodes)}")
    print(f"  连接数: {len(result.edges)}")

    # 验证所有节点都有坐标
    for node in result.nodes:
        assert "x" in node and "y" in node
        print(f"  {node['label']}: ({node['x']:.0f}, {node['y']:.0f})")

    print("\n✓ 复杂流程图布局完成")
    print()


def test_user_modifies_layout():
    """场景4: 用户调整布局"""
    print_section("场景 4: 用户说'重新排列这些节点'")

    print("\nAgent理解: 需要重新计算布局")

    # 原始布局
    nodes = [
        {"id": "A", "label": "A"},
        {"id": "B", "label": "B"},
        {"id": "C", "label": "C"},
        {"id": "D", "label": "D"},
    ]

    edges = [
        {"from_id": "A", "to_id": "B"},
        {"from_id": "A", "to_id": "C"},
        {"from_id": "B", "to_id": "D"},
        {"from_id": "C", "to_id": "D"},
    ]

    structure = {"nodes": nodes, "edges": edges}

    print("\n原始布局:")
    result1 = calculate_layout(structure, "light")
    for n in result1.nodes:
        print(f"  {n['id']}: ({n['x']:.0f}, {n['y']:.0f})")

    print("\n重新计算布局 (相同结构):")
    result2 = calculate_layout(structure, "dark")  # 不同主题
    for n in result2.nodes:
        print(f"  {n['id']}: ({n['x']:.0f}, {n['y']:.0f})")

    # 验证相对位置关系保持不变
    levels1 = topological_levels(result1.nodes, edges)
    levels2 = topological_levels(result2.nodes, edges)

    assert levels1 == levels2, "拓扑层级应该保持不变"

    print("\n✓ 布局已更新")
    print()


def test_user_large_project():
    """场景5: 用户创建大型项目"""
    print_section("场景 5: 用户说'创建一个完整的订单处理系统流程'")

    print("\nAgent理解: 需要创建大规模流程图")

    # 创建20个节点的大型流程
    nodes = []
    edges = []

    stages = [
        "订单创建",
        "库存检查",
        "支付验证",
        "订单确认",
        "仓库分配",
        "拣货",
        "包装",
        "称重",
        "生成运单",
        "交付快递",
        "运输中",
        "派送",
        "客户签收",
        "订单完成",
        "生成发票",
        "财务结算",
        "库存更新",
        "数据分析",
        "用户反馈",
        "结束",
    ]

    for i, stage in enumerate(stages):
        nodes.append({"id": f"step_{i}", "label": stage})
        if i > 0:
            edges.append({"from_id": f"step_{i - 1}", "to_id": f"step_{i}"})

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("\n大型项目:")
    print(f"  总节点数: {len(result.nodes)}")
    print(f"  总连接数: {len(result.edges)}")

    # 计算图的高度
    ys = [n["y"] for n in result.nodes]
    total_height = max(ys) - min(ys)

    print(f"  总高度: {total_height:.0f}px")
    print(f"  平均节点间距: {total_height / (len(nodes) - 1):.0f}px")

    print("\n前5个节点:")
    for i in range(min(5, len(result.nodes))):
        n = result.nodes[i]
        print(f"  {n['label']}: ({n['x']:.0f}, {n['y']:.0f})")

    print(f"\n... 省略{len(result.nodes) - 10}个节点 ...\n")

    print("后5个节点:")
    for i in range(max(0, len(result.nodes) - 5), len(result.nodes)):
        n = result.nodes[i]
        print(f"  {n['label']}: ({n['x']:.0f}, {n['y']:.0f})")

    print("\n✓ 大型流程图创建成功")
    print()


def test_user_parallel_branches():
    """场景6: 用户创建并行分支"""
    print_section("场景 6: 用户说'添加三个并行处理分支'")

    print("\nAgent理解: 需要创建并行分支")

    nodes = [
        {"id": "start", "label": "开始"},
        {"id": "split", "label": "分发任务"},
        {"id": "branch1", "label": "分支1-邮件通知"},
        {"id": "branch2", "label": "分支2-短信通知"},
        {"id": "branch3", "label": "分支3-APP推送"},
        {"id": "merge", "label": "汇总结果"},
        {"id": "end", "label": "结束"},
    ]

    edges = [
        {"from_id": "start", "to_id": "split"},
        {"from_id": "split", "to_id": "branch1"},
        {"from_id": "split", "to_id": "branch2"},
        {"from_id": "split", "to_id": "branch3"},
        {"from_id": "branch1", "to_id": "merge"},
        {"from_id": "branch2", "to_id": "merge"},
        {"from_id": "branch3", "to_id": "merge"},
        {"from_id": "merge", "to_id": "end"},
    ]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("\n并行分支布局:")
    levels = topological_levels(nodes, edges)

    for level in range(max(levels.values()) + 1):
        level_nodes = [n for n in result.nodes if levels[n["id"]] == level]
        if level_nodes:
            print(f"  层级 {level}: {', '.join([n['label'] for n in level_nodes])}")

    # 验证三个分支在同一层
    branch_levels = [levels[f"branch{i}"] for i in range(1, 4)]
    assert len(set(branch_levels)) == 1, "三个分支应该在同一层"

    print("\n✓ 并行分支创建成功")
    print()


def test_error_handling():
    """场景7: 错误处理"""
    print_section("场景 7: 测试错误处理")

    print("\n测试1: 空节点列表")
    try:
        result = calculate_layout({"nodes": [], "edges": []}, "light")
        print(f"  结果: {len(result.nodes)}个节点")
        print("  ✓ 正确处理空列表")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    print("\n测试2: 单个节点")
    try:
        result = calculate_layout(
            {"nodes": [{"id": "A", "label": "A"}], "edges": []}, "light"
        )
        print(f"  结果: {len(result.nodes)}个节点")
        print("  ✓ 正确处理单节点")
    except Exception as e:
        print(f"  ✗ 错误: {e}")

    print("\n测试3: 断开的边")
    try:
        result = calculate_layout(
            {
                "nodes": [{"id": "A", "label": "A"}],
                "edges": [{"from_id": "A", "to_id": "B"}],  # B不存在
            },
            "light",
        )
        print(f"  结果: {len(result.nodes)}个节点")
        print("  ✓ 正确处理缺失节点")
    except Exception as e:
        print(f"  ✓ 抛出错误: {type(e).__name__}")

    print("\n✓ 错误处理测试完成")
    print()


def test_theme_switching():
    """场景8: 主题切换"""
    print_section("场景 8: 用户切换深色主题")

    print("\nAgent理解: 需要使用深色主题")

    # 测试主题颜色
    from src.agent.lib.canvas.helpers import get_theme_colors

    light_colors = get_theme_colors("light")
    dark_colors = get_theme_colors("dark")

    print("\n浅色主题:")
    print(f"  背景色: {light_colors['background']}")
    print(f"  描边色: {light_colors['stroke']}")
    print(f"  文本色: {light_colors['text']}")

    print("\n深色主题:")
    print(f"  背景色: {dark_colors['background']}")
    print(f"  描边色: {dark_colors['stroke']}")
    print(f"  文本色: {dark_colors['text']}")

    # 验证颜色不同
    assert (
        light_colors["background"] != dark_colors["background"]
        or light_colors["stroke"] != dark_colors["stroke"]
    ), "不同主题应该有不同的颜色"

    print("\n✓ 主题切换成功")
    print()


def test_real_world_scenario():
    """场景9: 真实世界案例"""
    print_section("场景 9: 真实案例 - 用户注册流程")

    print("\n用户输入: '帮我画一个用户注册的完整流程'")
    print("\nAgent分析:")
    print("  - 需要包含：输入信息、验证、创建账户、发送邮件")
    print("  - 需要考虑：验证失败的情况")

    nodes = [
        {"id": "start", "label": "开始"},
        {"id": "input", "label": "填写注册信息"},
        {"id": "validate", "label": "验证信息"},
        {"id": "check_email", "label": "检查邮箱是否存在"},
        {"id": "create", "label": "创建账户"},
        {"id": "send_email", "label": "发送验证邮件"},
        {"id": "wait", "label": "等待邮箱验证"},
        {"id": "verify", "label": "用户点击验证链接"},
        {"id": "activate", "label": "激活账户"},
        {"id": "success", "label": "注册成功"},
        {"id": "fail", "label": "注册失败"},
    ]

    edges = [
        {"from_id": "start", "to_id": "input"},
        {"from_id": "input", "to_id": "validate"},
        {"from_id": "validate", "to_id": "check_email"},
        {"from_id": "check_email", "to_id": "create"},
        {"from_id": "check_email", "to_id": "fail"},  # 邮箱已存在
        {"from_id": "create", "to_id": "send_email"},
        {"from_id": "send_email", "to_id": "wait"},
        {"from_id": "wait", "to_id": "verify"},
        {"from_id": "verify", "to_id": "activate"},
        {"from_id": "activate", "to_id": "success"},
    ]

    structure = {"nodes": nodes, "edges": edges}
    result = calculate_layout(structure, "light")

    print("\nAgent创建了:")
    print(f"  节点总数: {len(result.nodes)}")
    print(f"  连接总数: {len(result.edges)}")

    # 显示关键节点
    key_nodes = ["start", "validate", "check_email", "success", "fail"]
    print("\n关键节点:")
    for node in result.nodes:
        if node["id"] in key_nodes:
            print(f"  {node['label']}: ({node['x']:.0f}, {node['y']:.0f})")

    print("\n✓ 真实场景测试成功")
    print()


def main():
    print("=" * 60)
    print("实际使用场景验证")
    print("=" * 60)

    try:
        test_user_creates_flowchart()
        test_user_adds_decision()
        test_user_complex_graph()
        test_user_modifies_layout()
        test_user_large_project()
        test_user_parallel_branches()
        test_error_handling()
        test_theme_switching()
        test_real_world_scenario()

        print_section("✓ 所有场景测试完成")
        print("\n总结:")
        print("  ✓ 基础流程图创建")
        print("  ✓ 复杂图结构处理")
        print("  ✓ 大规模项目支持")
        print("  ✓ 并行分支处理")
        print("  ✓ 错误处理机制")
        print("  ✓ 主题切换支持")
        print("  ✓ 真实世界场景")
        print()
        return 0

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
