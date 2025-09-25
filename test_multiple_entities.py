#!/usr/bin/env python3
"""
测试多个实体的识别和显示
"""

import requests
import json

def test_multiple_entities():
    """测试多个实体的识别"""
    
    test_cases = [
        {
            "text": "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects.",
            "expected_entities": ["A Round Financing", "ABA Bank Index", "A-Share"],
            "description": "包含三个金融实体的复杂句子"
        },
        {
            "text": "The company completed Series A funding and is considering an IPO.",
            "expected_entities": ["Series A", "IPO"],
            "description": "包含两个融资相关实体"
        },
        {
            "text": "A-share and B-share markets showed different performance.",
            "expected_entities": ["A-share", "B-share"],
            "description": "包含两个股票类型实体"
        },
        {
            "text": "Venture Capital firms are interested in the startup's A Round Financing.",
            "expected_entities": ["Venture Capital", "A Round Financing"],
            "description": "包含风险投资和融资实体"
        }
    ]
    
    print("测试多个实体的识别和显示")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['description']}")
        print(f"输入文本: '{test_case['text']}'")
        print(f"期望实体: {test_case['expected_entities']}")
        
        try:
            # 测试NER端点
            response = requests.post(
                "http://localhost:8000/finterm/ner",
                json={
                    "text": test_case['text'],
                    "classifications": ["L", "E"]  # Financing 和 Equities 类别
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("实体详情", [])
                
                print(f"\n实际识别结果:")
                print(f"识别实体数: {len(entities)}")
                
                if entities:
                    print("实体详情:")
                    for j, entity in enumerate(entities, 1):
                        original_term = entity.get("原始单词", "")
                        recognized_term = entity.get("识别实体", "")
                        category = entity.get("实体分类", "N/A")
                        score = entity.get("识别分数", "N/A")
                        start_pos = entity.get("开始字符位置", "N/A")
                        end_pos = entity.get("结束字符位置", "N/A")
                        
                        print(f"  {j}. 原始单词: '{original_term}'")
                        print(f"     识别实体: '{recognized_term}'")
                        print(f"     实体分类: {category}")
                        print(f"     识别分数: {score}")
                        print(f"     位置: [{start_pos}, {end_pos}]")
                        
                        # 检查是否在期望实体中
                        if recognized_term in test_case['expected_entities']:
                            print(f"     ✓ 正确识别")
                        else:
                            print(f"     ✗ 未在期望实体中找到")
                    
                    # 检查是否识别了所有期望的实体
                    recognized_entities = [entity.get("识别实体", "") for entity in entities]
                    missing_entities = [entity for entity in test_case['expected_entities'] if entity not in recognized_entities]
                    extra_entities = [entity for entity in recognized_entities if entity not in test_case['expected_entities']]
                    
                    if missing_entities:
                        print(f"\n  ✗ 缺失实体: {missing_entities}")
                    if extra_entities:
                        print(f"\n  ⚠ 额外识别实体: {extra_entities}")
                    if not missing_entities and not extra_entities:
                        print(f"\n  ✓ 完美匹配所有期望实体")
                        
                else:
                    print("  ✗ 未识别到任何实体")
            else:
                print(f"  ✗ NER请求失败: {response.status_code}")
                print(f"    响应: {response.text}")
                
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")

def test_specific_case():
    """测试特定案例"""
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print(f"\n测试特定案例")
    print("=" * 60)
    print(f"输入文本: '{test_text}'")
    
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
                    print(f"  {i}. {recognized_term}")
                    
                # 检查是否每个实体都是独立的
                print(f"\n实体独立性检查:")
                for i, entity in enumerate(entities, 1):
                    original_term = entity.get("原始单词", "")
                    recognized_term = entity.get("识别实体", "")
                    
                    if original_term == recognized_term and len(recognized_term.strip()) > 0:
                        print(f"  {i}. ✓ 实体独立: '{recognized_term}'")
                    else:
                        print(f"  {i}. ✗ 实体有问题: 原始='{original_term}', 识别='{recognized_term}'")
            else:
                print("  ✗ 未识别到任何实体")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    print("多个实体识别测试")
    print("确保后端服务器运行在 localhost:8000")
    print()
    
    test_multiple_entities()
    test_specific_case()
    
    print("\n测试完成！") 