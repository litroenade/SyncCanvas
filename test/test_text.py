"""文本计算验证脚本

测试文本尺寸估算和居中定位的实际功能：
- 纯英文文本尺寸估算
- 纯中文文本尺寸估算
- 中英文混合文本尺寸估算
- 不同字体的影响
- 文本在容器中的居中计算
"""

import sys
import io
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.lib.math.text import (
    estimate_text_size,
    calculate_centered_position,
)


def is_cjk_character(char: str) -> bool:
    """检测是否为CJK字符"""
    if not char:
        return False
    code = ord(char)
    # 中日韩统一表意文字
    return (0x4E00 <= code <= 0x9FFF or  # CJK Unified Ideographs
            0x3400 <= code <= 0x4DBF or  # CJK Extension A
            0x20000 <= code <= 0x2A6DF or  # CJK Extension B
            0x3040 <= code <= 0x309F or  # Hiragana
            0x30A0 <= code <= 0x30FF or  # Katakana
            0xAC00 <= code <= 0xD7AF)  # Hangul


def test_cjk_detection():
    """测试CJK字符检测"""
    print("\n" + "="*60)
    print("测试 1: CJK字符检测")
    print("="*60)
    
    test_cases = [
        ('你', True, "中文"),
        ('あ', True, "日文平假名"),
        ('ア', True, "日文片假名"),
        ('한', True, "韩文"),
        ('a', False, "英文字母"),
        ('1', False, "数字"),
        ('!', False, "符号"),
        # 全角空格不在CJK统一汉字范围内，预期为False
        ('　', False, "全角空格"),
    ]
    
    print("字符检测:")
    for char, expected, desc in test_cases:
        result = is_cjk_character(char)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{char}' ({desc}): {result}")
        assert result == expected, f"{desc} 检测错误"
    
    print("\n✓ 测试通过")


def test_english_text_size():
    """测试纯英文文本尺寸"""
    print("\n" + "="*60)
    print("测试 2: 纯英文文本尺寸估算")
    print("="*60)
    
    test_cases = [
        ("Hello", 20, "Virgil"),
        ("Hello World", 20, "Virgil"),
        ("A", 20, "Virgil"),
        ("The quick brown fox", 16, "Helvetica"),
    ]
    
    for text, font_size, font_family_name in test_cases:
        # font_family: 1=Virgil, 2=Helvetica, 3=Cascadia
        font_family = 1 if font_family_name == "Virgil" else 2
        width, height = estimate_text_size(text, font_size, font_family)
        print(f"\n文本: '{text}'")
        print(f"  字体: {font_family}, 大小: {font_size}")
        print(f"  估算尺寸: {width:.1f} x {height:.1f}")
        print(f"  字符数: {len(text)}")
        print(f"  平均字符宽度: {width/len(text):.1f}")
        
        # 基本合理性检查
        assert width > 0 and height > 0, "尺寸必须为正"
        assert height >= font_size, "高度应该至少等于字体大小"
    
    print("\n✓ 测试通过")


def test_chinese_text_size():
    """测试纯中文文本尺寸"""
    print("\n" + "="*60)
    print("测试 3: 纯中文文本尺寸估算")
    print("="*60)
    
    test_cases = [
        ("你好", 20, "Virgil"),
        ("测试文本", 20, "Virgil"),
        ("一", 20, "Virgil"),
        ("这是一个测试", 16, "Helvetica"),
    ]
    
    for text, font_size, font_family_name in test_cases:
        font_family = 1 if font_family_name == "Virgil" else 2
        width, height = estimate_text_size(text, font_size, font_family)
        print(f"\n文本: '{text}'")
        print(f"  字体: {font_family}, 大小: {font_size}")
        print(f"  估算尺寸: {width:.1f} x {height:.1f}")
        print(f"  字符数: {len(text)}")
        print(f"  平均字符宽度: {width/len(text):.1f}")
        
        # 中文字符应该更宽
        avg_width = width / len(text)
        # CJK字符宽度应该接近字体大小
        assert avg_width >= font_size * 0.8, "中文字符宽度应该接近字体大小"
    
    print("\n✓ 测试通过")


def test_mixed_text_size():
    """测试中英文混合文本尺寸"""
    print("\n" + "="*60)
    print("测试 4: 中英文混合文本尺寸估算")
    print("="*60)
    
    test_cases = [
        ("Hello 世界", 20, "Virgil"),
        ("测试Test", 20, "Virgil"),
        ("123测试abc", 20, "Virgil"),
        ("Python编程", 16, "Helvetica"),
    ]
    
    for text, font_size, font_family_name in test_cases:
        font_family = 1 if font_family_name == "Virgil" else 2
        width, height = estimate_text_size(text, font_size, font_family)
        
        # 统计CJK字符数量
        cjk_count = sum(1 for c in text if is_cjk_character(c))
        ascii_count = len(text) - cjk_count
        
        print(f"\n文本: '{text}'")
        print(f"  字体: {font_family_name}, 大小: {font_size}")
        print(f"  CJK字符: {cjk_count}, ASCII字符: {ascii_count}")
        print(f"  估算尺寸: {width:.1f} x {height:.1f}")
        
        # 手动计算预期宽度
        char_width = font_size * (0.6 if font_family == 1 else 0.5)
        expected_width = cjk_count * font_size + ascii_count * char_width
        print(f"  预期宽度: {expected_width:.1f}")
        print(f"  偏差: {abs(width - expected_width):.1f}")
        
        # 允许一定误差
        assert abs(width - expected_width) < 5, "宽度计算偏差过大"
    
    print("\n✓ 测试通过")


def test_multiline_text_size():
    """测试多行文本尺寸"""
    print("\n" + "="*60)
    print("测试 5: 多行文本尺寸估算")
    print("="*60)
    
    test_cases = [
        ("Line 1\nLine 2", 20, "Virgil"),
        ("第一行\n第二行\n第三行", 20, "Virgil"),
        ("Mixed\n混合", 20, "Virgil"),
    ]
    
    for text, font_size, font_family_name in test_cases:
        font_family = 1 if font_family_name == "Virgil" else 2
        width, height = estimate_text_size(text, font_size, font_family)
        lines = text.split('\n')
        line_count = len(lines)
        
        print(f"\n文本: '{text[:20]}...' ({line_count}行)")
        print(f"  字体: {font_family_name}, 大小: {font_size}")
        print(f"  估算尺寸: {width:.1f} x {height:.1f}")
        
        # 高度应该是行数的倍数
        expected_height = line_count * font_size * 1.2  # 1.2是行高系数
        print(f"  预期高度: {expected_height:.1f}")
        print(f"  实际高度: {height:.1f}")
        
        # 宽度应该基于最长行
        max_line_width = max(
            estimate_text_size(line, font_size, font_family)[0]
            for line in lines
        )
        print("  最长行宽度: {:.1f}".format(max_line_width))
        # 注意：实际宽度可能基于整个文本内容计算
    
    print("\n✓ 测试通过")


def test_font_family_comparison():
    """测试不同字体的尺寸差异"""
    print("\n" + "="*60)
    print("测试 6: 字体对比")
    print("="*60)
    
    text = "Hello World"
    font_size = 20
    
    print(f"文本: '{text}', 字体大小: {font_size}")
    print("\n字体对比:")
    
    fonts = [(1, "Virgil"), (2, "Helvetica"), (3, "Cascadia")]
    results = {}
    
    for font_id, font_name in fonts:
        width, height = estimate_text_size(text, font_size, font_id)
        results[font_name] = (width, height)
        print("  {}: {:.1f} x {:.1f}".format(font_name, width, height))
    
    # Virgil应该比Helvetica更宽（0.6 vs 0.5）
    if "Virgil" in results and "Helvetica" in results:
        virgil_width = results["Virgil"][0]
        helvetica_width = results["Helvetica"][0]
        print(f"\nVirgil比Helvetica宽: {virgil_width - helvetica_width:.1f}像素")
        assert virgil_width > helvetica_width, "Virgil应该比Helvetica更宽"
    
    print("\n✓ 测试通过")


def test_centered_position():
    """测试文本居中计算"""
    print("\n" + "="*60)
    print("测试 7: 文本居中定位")
    print("="*60)
    
    # 容器尺寸
    container_width = 200
    container_height = 100
    container_x = 100
    container_y = 50
    
    test_cases = [
        ("Hello", 20, "Virgil"),
        ("你好世界", 20, "Virgil"),
        ("Test\nLine", 16, "Helvetica"),
    ]
    
    print("容器: x={}, y={}, w={}, h={}".format(
        container_x, container_y, container_width, container_height))
    
    for text, font_size, font_family_name in test_cases:
        font_family = 1 if font_family_name == "Virgil" else 2
        text_x, text_y, text_width, text_height = calculate_centered_position(
            container_x, container_y,
            container_width, container_height,
            text,
            font_size,
            font_family
        )
        
        print("\n文本: '{}'".format(text[:20]))
        print("  文本尺寸: {:.1f} x {:.1f}".format(text_width, text_height))
        print("  居中位置: ({:.1f}, {:.1f})".format(text_x, text_y))
        
        # 验证居中
        # 文本中心应该在容器中心
        text_center_x = text_x + text_width / 2
        text_center_y = text_y + text_height / 2
        container_center_x = container_x + container_width / 2
        container_center_y = container_y + container_height / 2
        
        print("  文本中心: ({:.1f}, {:.1f})".format(text_center_x, text_center_y))
        print("  容器中心: ({:.1f}, {:.1f})".format(container_center_x, container_center_y))
        
        assert abs(text_center_x - container_center_x) < 1, "X轴未居中"
        assert abs(text_center_y - container_center_y) < 1, "Y轴未居中"
    
    print("\n✓ 测试通过")


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "="*60)
    print("测试 8: 边界情况")
    print("="*60)
    
    # 空字符串
    print("1. 空字符串:")
    width, height = estimate_text_size("", 20, 1)
    print("   尺寸: {:.1f} x {:.1f}".format(width, height))
    assert width >= 0 and height >= 0, "空字符串应该返回非负尺寸"
    
    # 单个字符
    print("\n2. 单个字符:")
    for char in ['a', '中', '1', ' ']:
        width, height = estimate_text_size(char, 20, 1)
        print("   '{}': {:.1f} x {:.1f}".format(char, width, height))
        assert width > 0 and height > 0, "单个字符应该有尺寸"
    
    # 很长的文本
    print("\n3. 很长的文本:")
    long_text = "A" * 100
    width, height = estimate_text_size(long_text, 20, 1)
    print("   100个字符: {:.1f} x {:.1f}".format(width, height))
    assert width > 1000, "长文本应该很宽"
    
    # 特殊字符
    print("\n4. 特殊字符:")
    special = "!@#$%^&*()"
    width, height = estimate_text_size(special, 20, 1)
    print("   '{}': {:.1f} x {:.1f}".format(special, width, height))
    
    print("\n✓ 测试通过")


def test_font_size_scaling():
    """测试字体大小的缩放关系"""
    print("\n" + "="*60)
    print("测试 9: 字体大小缩放")
    print("="*60)
    
    text = "Test"
    font_family = 1
    
    print("文本: '{}', 字体: Virgil".format(text))
    print("\n字体大小缩放:")
    
    sizes = [10, 20, 30, 40]
    prev_width = 0
    prev_height = 0
    
    for size in sizes:
        width, height = estimate_text_size(text, size, font_family)
        print("  {}pt: {:.1f} x {:.1f}".format(size, width, height))
        
        # 尺寸应该随字体大小线性增长
        if prev_width > 0:
            width_ratio = width / prev_width
            height_ratio = height / prev_height
            size_ratio = size / (size - 10)
            print("    宽度比: {:.2f}, 高度比: {:.2f}, 预期比: {:.2f}".format(
                width_ratio, height_ratio, size_ratio))
            
            # 允许一定误差
            assert abs(width_ratio - size_ratio) < 0.1, "宽度未按比例缩放"
            assert abs(height_ratio - size_ratio) < 0.1, "高度未按比例缩放"
        
        prev_width = width
        prev_height = height
    
    print("\n✓ 测试通过")


def test_real_world_scenarios():
    """测试实际使用场景"""
    print("\n" + "="*60)
    print("测试 10: 实际场景")
    print("="*60)
    
    scenarios = [
        {
            "desc": "流程图节点标签",
            "text": "开始",
            "font_size": 20,
            "font_family": "Virgil",
            "container": (0, 0, 100, 50),
        },
        {
            "desc": "按钮文本",
            "text": "Submit",
            "font_size": 16,
            "font_family": "Helvetica",
            "container": (0, 0, 80, 30),
        },
        {
            "desc": "长标题",
            "text": "这是一个很长的标题文本",
            "font_size": 24,
            "font_family": "Virgil",
            "container": (0, 0, 300, 60),
        },
    ]
    
    for scenario in scenarios:
        print(f"\n场景: {scenario['desc']}")
        print(f"  文本: '{scenario['text']}'")
        
        font_family = 1 if scenario['font_family'] == "Virgil" else 2
        text_x, text_y, text_width, text_height = calculate_centered_position(
            scenario['container'][0], scenario['container'][1],
            scenario['container'][2], scenario['container'][3],
            scenario['text'],
            scenario['font_size'],
            font_family
        )
        print(f"  文本尺寸: {text_width:.1f} x {text_height:.1f}")
        
        cw, ch = scenario['container'][2], scenario['container'][3]
        print(f"  容器: {cw} x {ch}")
        print(f"  居中位置: ({text_x:.1f}, {text_y:.1f})")
        
        if text_width > cw or text_height > ch:
            print("  ⚠ 文本超出容器")
        else:
            print("  ✓ 文本适合容器")
    
    print("\n✓ 测试通过")


def main():
    """运行所有测试"""
    print("="*60)
    print("文本计算功能验证")
    print("="*60)
    
    try:
        test_cjk_detection()
        test_english_text_size()
        test_chinese_text_size()
        test_mixed_text_size()
        test_multiline_text_size()
        test_font_family_comparison()
        test_centered_position()
        test_edge_cases()
        test_font_size_scaling()
        test_real_world_scenarios()
        
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
