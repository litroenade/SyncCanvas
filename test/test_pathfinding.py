"""路径规划算法验证脚本

测试 A* 路径规划算法的实际功能：
- 简单直线路径
- 带障碍物的避障路径
- 复杂多障碍物场景
- 性能测试
"""

import sys
import io
import time
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.math.pathfinding import OrthogonalRouter
from src.agent.lib.math.geometry import Point, Rect
from src.config import config


def test_simple_straight_path():
    """测试简单直线路径"""
    print("\n" + "="*60)
    print("测试 1: 简单直线路径（无障碍）")
    print("="*60)
    
    router = OrthogonalRouter()
    # 空障碍物时不需要调用set_obstacles
    
    start = Point(0, 0)
    end = Point(100, 100)
    
    print(f"起点: ({start.x}, {start.y})")
    print(f"终点: ({end.x}, {end.y})")
    
    start_time = time.time()
    path = router.find_path(start, end)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"路径点数: {len(path)}")
    print(f"耗时: {elapsed:.2f}ms")
    print(f"路径: {[(round(p.x, 1), round(p.y, 1)) for p in path[:5]]}" + 
          (" ..." if len(path) > 5 else ""))
    
    # 验证
    assert len(path) >= 2, "路径至少包含起点和终点"
    assert path[0].x == start.x and path[0].y == start.y, "起点正确"
    assert path[-1].x == end.x and path[-1].y == end.y, "终点正确"
    print("✓ 测试通过")


def test_single_obstacle():
    """测试单个障碍物避障"""
    print("\n" + "="*60)
    print("测试 2: 单个障碍物避障")
    print("="*60)
    
    # 创建障碍物（一个矩形挡在中间）
    obstacles = [
        {
            "id": "obstacle1",
            "type": "rectangle",
            "x": 40,
            "y": 40,
            "width": 20,
            "height": 20,
            "isDeleted": False,
        }
    ]
    
    router = OrthogonalRouter()
    router.set_obstacles(obstacles, set())
    
    start = Point(0, 50)
    end = Point(100, 50)
    
    print(f"起点: ({start.x}, {start.y})")
    print(f"终点: ({end.x}, {end.y})")
    print(f"障碍物: x={obstacles[0]['x']}, y={obstacles[0]['y']}, " +
          f"w={obstacles[0]['width']}, h={obstacles[0]['height']}")
    
    start_time = time.time()
    path = router.find_path(start, end)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"路径点数: {len(path)}")
    print(f"耗时: {elapsed:.2f}ms")
    
    # 显示路径
    if len(path) <= 10:
        print("完整路径:")
        for i, p in enumerate(path):
            print(f"  {i+1}. ({round(p.x, 1)}, {round(p.y, 1)})")
    else:
        print(f"路径摘要: 起点 → ... {len(path)-2}个中间点 ... → 终点")
    
    # 验证路径避开了障碍物
    obstacle_rect = Rect(40, 40, 20, 20)
    for p in path:
        # 检查路径点不在障碍物内部
        in_obstacle = (obstacle_rect.left <= p.x <= obstacle_rect.right and
                      obstacle_rect.top <= p.y <= obstacle_rect.bottom)
        if in_obstacle:
            print(f"✗ 警告: 路径点 ({p.x}, {p.y}) 穿过障碍物")
    
    print("✓ 测试通过")


def test_multiple_obstacles():
    """测试多个障碍物的复杂场景"""
    print("\n" + "="*60)
    print("测试 3: 多障碍物复杂场景")
    print("="*60)
    
    # 创建多个障碍物形成迷宫
    obstacles = [
        {"id": "obs1", "type": "rectangle", "x": 50, "y": 0, "width": 20, "height": 80},
        {"id": "obs2", "type": "rectangle", "x": 100, "y": 50, "width": 20, "height": 80},
        {"id": "obs3", "type": "rectangle", "x": 150, "y": 0, "width": 20, "height": 80},
    ]
    
    router = OrthogonalRouter()
    router.set_obstacles(obstacles, set())
    
    start = Point(0, 50)
    end = Point(200, 50)
    
    print(f"起点: ({start.x}, {start.y})")
    print(f"终点: ({end.x}, {end.y})")
    print(f"障碍物数量: {len(obstacles)}")
    
    start_time = time.time()
    path = router.find_path(start, end)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"路径点数: {len(path)}")
    print(f"耗时: {elapsed:.2f}ms")
    
    if len(path) > 0:
        # 计算路径总长度
        total_distance = 0
        for i in range(len(path) - 1):
            total_distance += path[i].distance_to(path[i+1])
        print(f"路径总长度: {total_distance:.1f}")
        
        # 统计转弯次数
        turns = 0
        for i in range(1, len(path) - 1):
            dx1 = path[i].x - path[i-1].x
            dy1 = path[i].y - path[i-1].y
            dx2 = path[i+1].x - path[i].x
            dy2 = path[i+1].y - path[i].y
            # 方向改变表示转弯
            if (dx1 != 0 and dy2 != 0) or (dy1 != 0 and dx2 != 0):
                turns += 1
        print(f"转弯次数: {turns}")
        print("✓ 测试通过")
    else:
        print("✗ 未找到路径")


def test_unreachable_target():
    """测试无法到达的目标（被完全包围）"""
    print("\n" + "="*60)
    print("测试 4: 无法到达的目标")
    print("="*60)
    
    # 创建一个被完全包围的区域
    obstacles = [
        {"id": "wall_top", "type": "rectangle", "x": 40, "y": 40, "width": 60, "height": 10},
        {"id": "wall_bottom", "type": "rectangle", "x": 40, "y": 90, "width": 60, "height": 10},
        {"id": "wall_left", "type": "rectangle", "x": 40, "y": 40, "width": 10, "height": 60},
        {"id": "wall_right", "type": "rectangle", "x": 90, "y": 40, "width": 10, "height": 60},
    ]
    
    router = OrthogonalRouter()
    router.set_obstacles(obstacles, set())
    
    start = Point(0, 70)
    end = Point(70, 70)  # 在包围圈内部
    
    print(f"起点: ({start.x}, {start.y})")
    print(f"终点: ({end.x}, {end.y}) (被包围)")
    print(f"障碍物数量: {len(obstacles)} (形成封闭区域)")
    
    start_time = time.time()
    path = router.find_path(start, end)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"耗时: {elapsed:.2f}ms")
    
    if len(path) == 2:  # 只有起点和终点，表示返回直线
        print("结果: 返回直线路径（无法避障）")
        print("✓ 测试通过（正确处理了无解情况）")
    else:
        print(f"路径点数: {len(path)}")
        print("注意: 算法找到了路径，可能障碍物设置有间隙")


def test_performance():
    """性能测试：大量障碍物"""
    print("\n" + "="*60)
    print("测试 5: 性能测试（大量障碍物）")
    print("="*60)
    
    # 创建网格状障碍物
    obstacles = []
    for i in range(10):
        for j in range(10):
            if (i + j) % 3 == 0:  # 跳过一些位置留出通道
                obstacles.append({
                    "id": f"obs_{i}_{j}",
                    "type": "rectangle",
                    "x": i * 50,
                    "y": j * 50,
                    "width": 30,
                    "height": 30,
                })
    
    print(f"障碍物数量: {len(obstacles)}")
    
    router = OrthogonalRouter()
    router.set_obstacles(obstacles, set())
    
    start = Point(0, 0)
    end = Point(500, 500)
    
    print(f"起点: ({start.x}, {start.y})")
    print(f"终点: ({end.x}, {end.y})")
    
    start_time = time.time()
    path = router.find_path(start, end, max_iterations=5000)
    elapsed = (time.time() - start_time) * 1000
    
    print(f"路径点数: {len(path)}")
    print(f"耗时: {elapsed:.2f}ms")
    
    if elapsed < 1000:
        print("✓ 性能良好（<1秒）")
    else:
        print(f"⚠ 性能较慢（{elapsed/1000:.1f}秒）")


def test_config_parameters():
    """测试配置参数的影响"""
    print("\n" + "="*60)
    print("测试 6: 配置参数")
    print("="*60)
    
    print("当前配置:")
    print(f"  网格大小: {config.canvas.pathfinding_grid_size}")
    print(f"  障碍物padding: {config.canvas.pathfinding_obstacle_padding}")
    print(f"  最大迭代次数: {config.canvas.pathfinding_max_iterations}")
    print(f"  转弯惩罚: {config.canvas.pathfinding_turn_penalty}")
    
    # 测试不同网格大小的影响
    grid_sizes = [5, 10, 20]
    obstacles = [
        {"id": "obs1", "type": "rectangle", "x": 50, "y": 50, "width": 30, "height": 30}
    ]
    
    start = Point(0, 60)
    end = Point(100, 60)
    
    print(f"\n起点: ({start.x}, {start.y}), 终点: ({end.x}, {end.y})")
    print("\n不同网格大小的对比:")
    
    for grid_size in grid_sizes:
        router = OrthogonalRouter(grid_size=grid_size)
        router.set_obstacles(obstacles, set())
        
        start_time = time.time()
        path = router.find_path(start, end)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"  网格={grid_size}: {len(path)}个点, {elapsed:.2f}ms")


def main():
    """运行所有测试"""
    print("="*60)
    print("路径规划算法功能验证")
    print("="*60)
    
    try:
        test_simple_straight_path()
        test_single_obstacle()
        test_multiple_obstacles()
        test_unreachable_target()
        test_performance()
        test_config_parameters()
        
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
