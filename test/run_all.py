"""运行所有功能验证脚本"""

import sys
import io
import subprocess
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPTS = [
    ("test_pathfinding.py", "路径规划算法"),
    ("test_layout.py", "流程图布局算法"),
    ("test_geometry.py", "几何计算"),
    ("test_text.py", "文本计算"),
    ("test_elements.py", "元素操作"),
    ("test_agent_tools.py", "Agent工具"),
    ("test_scenarios.py", "实际使用场景"),
]


def run_script(script_name):
    """运行单个脚本"""
    script_path = Path(__file__).parent / script_name
    
    print(f"\n{'='*70}")
    print(f"运行: {script_name}")
    print('='*70)
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=False,
        text=True
    )
    
    return result.returncode


def main():
    """运行所有测试脚本"""
    print("="*70)
    print("SyncCanvas 功能验证测试套件")
    print("="*70)
    
    results = {}
    
    for script_name, description in SCRIPTS:
        print(f"\n开始测试: {description}")
        returncode = run_script(script_name)
        results[script_name] = (returncode == 0)
    
    # 汇总结果
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    for script_name, description in SCRIPTS:
        status = "✓ 通过" if results[script_name] else "✗ 失败"
        print(f"  {status} - {description} ({script_name})")
    
    # 统计
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
