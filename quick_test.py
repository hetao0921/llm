#!/usr/bin/env python3
"""
快速测试多个实体识别
"""

import requests
import json

def quick_test():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("快速测试多个实体识别")
    print("=" * 50)
    print(f"输入文本: {test_text}")
    
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
                    
                    print(f"  {i}. 识别实体: '{recognized_term}'")
                    print(f"     原始单词: '{original_term}'")
                    print(f"     分类: {category}")
                    print(f"     分数: {score}")
                    
                    # 检查是否是正确的独立实体
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

if __name__ == "__main__":
    quick_test() 