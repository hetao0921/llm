#!/usr/bin/env python3
"""
测试修复后的NER功能
"""

import requests
import json

def test_ner_fix():
    """测试NER修复后的功能"""
    
    test_cases = [
        "A Round Financing",
        "A Round Financing.",
        "My company has A Round Financing",
        "The company completed A Round Financing last year",
        "We are looking for A Round Financing opportunities",
        "A Round Financing is a type of venture capital funding",
        "A-share",
        "my company has a A-share.",
        "The company issued A-share to raise capital"
    ]
    
    print("测试修复后的NER功能")
    print("=" * 50)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试 {i}: '{test_text}'")
        
        try:
            # 测试NER端点
            response = requests.post(
                "http://localhost:8000/finterm/ner",
                json={
                    "text": test_text,
                    "classifications": ["L", "E"]  # Financing 和 Equities 类别
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("实体详情", [])
                
                if entities:
                    print(f"  ✓ 找到 {len(entities)} 个实体:")
                    for entity in entities:
                        original_term = entity.get("原始单词", "")
                        recognized_term = entity.get("识别实体", "")
                        category = entity.get("实体分类", "N/A")
                        score = entity.get("识别分数", "N/A")
                        start_pos = entity.get("开始字符位置", "N/A")
                        end_pos = entity.get("结束字符位置", "N/A")
                        
                        print(f"    - 原始单词: '{original_term}'")
                        print(f"    - 识别实体: '{recognized_term}'")
                        print(f"    - 实体分类: {category}")
                        print(f"    - 识别分数: {score}")
                        print(f"    - 位置: [{start_pos}, {end_pos}]")
                        
                        # 检查是否正确识别
                        if original_term == recognized_term and original_term:
                            print(f"    ✓ 识别正确，保持原始格式")
                        else:
                            print(f"    ✗ 识别有问题")
                            
                        # 检查是否包含完整术语
                        if "A Round Financing" in test_text and "A Round Financing" in original_term:
                            print(f"    ✓ 正确识别了 'A Round Financing'")
                        elif "A-share" in test_text and "A-share" in original_term:
                            print(f"    ✓ 正确识别了 'A-share'")
                else:
                    print(f"  ✗ 未找到实体")
            else:
                print(f"  ✗ NER请求失败: {response.status_code}")
                print(f"    响应: {response.text}")
                
        except Exception as e:
            print(f"  ✗ NER测试失败: {e}")

def test_specific_case():
    """测试特定案例"""
    test_text = "A Round Financing."
    
    print(f"\n测试特定案例: '{test_text}'")
    print("=" * 50)
    
    try:
        response = requests.post(
            "http://localhost:8000/finterm/ner",
            json={
                "text": test_text,
                "classifications": ["L"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("实体详情", [])
            
            if entities:
                print(f"✓ 找到 {len(entities)} 个实体:")
                for entity in entities:
                    original_term = entity.get("原始单词", "")
                    recognized_term = entity.get("识别实体", "")
                    print(f"  - 原始单词: '{original_term}'")
                    print(f"  - 识别实体: '{recognized_term}'")
                    
                    # 检查是否解决了"ancing"问题
                    if "ancing" in original_term or "ancing" in recognized_term:
                        print(f"  ✗ 仍然有问题：识别到了 'ancing'")
                    else:
                        print(f"  ✓ 问题已解决：正确识别了完整术语")
            else:
                print("✗ 未找到实体")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    print("NER修复测试")
    print("确保后端服务器运行在 localhost:8000")
    print()
    
    test_ner_fix()
    test_specific_case()
    
    print("\n测试完成！") 