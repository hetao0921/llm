#!/usr/bin/env python3
"""
测试标准化服务的修复效果
"""

import requests
import json

def test_normalization_fix():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("测试标准化服务修复效果")
    print("=" * 60)
    print(f"输入文本: {test_text}")
    print(f"期望实体: ['A Round Financing', 'ABA Bank Index', 'A-Share']")
    
    try:
        print("\n" + "="*60)
        print("发送标准化请求...")
        print("="*60)
        
        response = requests.post(
            "http://localhost:8000/finterm/normalize",
            json={
                "text": test_text,
                "classifications": ["L", "E"],
                "collection_name": "my_finterm_collection"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("实体详情", [])
            
            print("\n" + "="*60)
            print("最终标准化结果")
            print("="*60)
            print(f"识别实体数: {len(entities)}")
            
            if entities:
                print("\n最终实体详情:")
                for i, entity in enumerate(entities, 1):
                    recognized_term = entity.get("识别实体", "")
                    normalized_term = entity.get("标准化术语", "")
                    category = entity.get("实体分类", "N/A")
                    ner_score = entity.get("识别实体识别分数", "N/A")
                    norm_score = entity.get("匹配的标准化术语准确度", "N/A")
                    start_pos = entity.get("开始字符位置", "N/A")
                    end_pos = entity.get("结束字符位置", "N/A")
                    
                    print(f"  {i}. 识别实体: '{recognized_term}'")
                    print(f"     标准化术语: '{normalized_term}'")
                    print(f"     实体分类: {category}")
                    print(f"     NER识别分数: {ner_score}")
                    print(f"     标准化准确度: {norm_score}")
                    print(f"     位置: [{start_pos}, {end_pos}]")
                    
                    # 检查是否是正确的实体
                    if recognized_term in ["A Round Financing", "ABA Bank Index", "A-Share"]:
                        print(f"     ✓ 正确识别")
                    else:
                        print(f"     ✗ 可能有问题")
                        
            else:
                print("  ✗ 未识别到任何实体")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_simple_normalization():
    """测试简单案例的标准化"""
    test_text = "A Round Financing"
    
    print("\n" + "="*60)
    print("测试简单案例标准化")
    print("="*60)
    print(f"输入文本: {test_text}")
    
    try:
        response = requests.post(
            "http://localhost:8000/finterm/normalize",
            json={
                "text": test_text,
                "classifications": ["L"],
                "collection_name": "my_finterm_collection"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("实体详情", [])
            
            print(f"\n识别结果: {len(entities)} 个实体")
            for entity in entities:
                recognized_term = entity.get("识别实体", "")
                normalized_term = entity.get("标准化术语", "")
                ner_score = entity.get("识别实体识别分数", "N/A")
                norm_score = entity.get("匹配的标准化术语准确度", "N/A")
                print(f"  - 识别: '{recognized_term}' (NER分数: {ner_score})")
                print(f"    标准化: '{normalized_term}' (准确度: {norm_score})")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_normalization_fix()
    test_simple_normalization()
    print("\n测试完成！") 