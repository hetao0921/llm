#!/usr/bin/env python3
"""
测试NER的详细打印功能
"""

import requests
import json

def test_detailed_ner():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("测试NER详细打印功能")
    print("=" * 60)
    print(f"输入文本: {test_text}")
    print(f"期望实体: ['A Round Financing', 'ABA Bank Index', 'A-Share']")
    
    try:
        print("\n" + "="*60)
        print("发送NER请求...")
        print("="*60)
        
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
            
            print("\n" + "="*60)
            print("最终识别结果")
            print("="*60)
            print(f"识别实体数: {len(entities)}")
            
            if entities:
                print("\n最终实体详情:")
                for i, entity in enumerate(entities, 1):
                    recognized_term = entity.get("识别实体", "")
                    original_term = entity.get("原始单词", "")
                    category = entity.get("实体分类", "N/A")
                    score = entity.get("识别分数", "N/A")
                    start_pos = entity.get("开始字符位置", "N/A")
                    end_pos = entity.get("结束字符位置", "N/A")
                    
                    print(f"  {i}. 识别实体: '{recognized_term}'")
                    print(f"     原始单词: '{original_term}'")
                    print(f"     实体分类: {category}")
                    print(f"     识别分数: {score}")
                    print(f"     位置: [{start_pos}, {end_pos}]")
                    
                    # 检查准确度
                    if recognized_term in ["A Round Financing", "ABA Bank Index", "A-Share"]:
                        print(f"     ✓ 准确识别")
                    else:
                        print(f"     ✗ 可能不准确")
                        
            else:
                print("  ✗ 未识别到任何实体")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_simple_case():
    """测试简单案例"""
    test_text = "A Round Financing"
    
    print("\n" + "="*60)
    print("测试简单案例")
    print("="*60)
    print(f"输入文本: {test_text}")
    
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
            
            print(f"\n识别结果: {len(entities)} 个实体")
            for entity in entities:
                print(f"  - '{entity.get('识别实体', '')}' (分数: {entity.get('识别分数', 'N/A')})")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_detailed_ner()
    test_simple_case()
    print("\n测试完成！") 