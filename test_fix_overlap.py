#!/usr/bin/env python3
"""
测试重叠实体过滤的修复效果
"""

import requests
import json

def test_overlap_fix():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("测试重叠实体过滤修复")
    print("=" * 50)
    print(f"输入文本: {test_text}")
    print(f"期望实体: ['A Round Financing', 'ABA Bank Index', 'A-Share']")
    
    try:
        response = requests.post(
            "http://localhost:8000/finterm/ner",
            json={
                "text": test_text,
                "classifications": ["L", "E"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("实体详情", [])
            
            print(f"\n识别结果:")
            print(f"识别实体数: {len(entities)}")
            
            if entities:
                print("\n实际识别实体:")
                for i, entity in enumerate(entities, 1):
                    recognized_term = entity.get("识别实体", "")
                    original_term = entity.get("原始单词", "")
                    category = entity.get("实体分类", "N/A")
                    score = entity.get("识别分数", "N/A")
                    start_pos = entity.get("开始字符位置", "N/A")
                    end_pos = entity.get("结束字符位置", "N/A")
                    
                    print(f"  {i}. 识别实体: '{recognized_term}'")
                    print(f"     原始单词: '{original_term}'")
                    print(f"     分类: {category}")
                    print(f"     分数: {score}")
                    print(f"     位置: [{start_pos}, {end_pos}]")
                    print(f"     长度: {len(recognized_term)}")
                    
                    # 检查是否是正确的实体
                    if recognized_term in ["A Round Financing", "ABA Bank Index", "A-Share"]:
                        print(f"     ✓ 正确识别")
                    elif "Bank Index" in recognized_term and "ABA" not in recognized_term:
                        print(f"     ✗ 错误识别了子字符串")
                    elif len(recognized_term) > 50:
                        print(f"     ✗ 实体太长，可能是整个句子")
                    else:
                        print(f"     ⚠ 其他实体")
                
                # 检查是否识别了所有期望的实体
                recognized_entities = [entity.get("识别实体", "") for entity in entities]
                expected_entities = ["A Round Financing", "ABA Bank Index", "A-Share"]
                
                missing_entities = [entity for entity in expected_entities if entity not in recognized_entities]
                extra_entities = [entity for entity in recognized_entities if entity not in expected_entities]
                
                if missing_entities:
                    print(f"\n  ✗ 缺失实体: {missing_entities}")
                if extra_entities:
                    print(f"\n  ⚠ 额外识别实体: {extra_entities}")
                if not missing_entities and not extra_entities:
                    print(f"\n  ✓ 完美匹配所有期望实体")
                    
            else:
                print("  ✗ 未识别到任何实体")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_other_cases():
    """测试其他案例"""
    test_cases = [
        {
            "text": "The company completed Series A funding and is considering an IPO.",
            "expected": ["Series A", "IPO"]
        },
        {
            "text": "A-share and B-share markets showed different performance.",
            "expected": ["A-share", "B-share"]
        }
    ]
    
    print("\n" + "=" * 50)
    print("测试其他案例")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}:")
        print(f"输入: {test_case['text']}")
        print(f"期望: {test_case['expected']}")
        
        try:
            response = requests.post(
                "http://localhost:8000/finterm/ner",
                json={
                    "text": test_case['text'],
                    "classifications": ["L", "E"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("实体详情", [])
                recognized_entities = [entity.get("识别实体", "") for entity in entities]
                
                print(f"实际识别: {recognized_entities}")
                
                if recognized_entities == test_case['expected']:
                    print("✓ 完美匹配")
                else:
                    print("✗ 不匹配")
            else:
                print(f"✗ 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_overlap_fix()
    test_other_cases()
    print("\n测试完成！") 