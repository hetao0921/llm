#!/usr/bin/env python3
"""
测试高亮文本功能
"""

import requests
import json

def test_highlight_ner():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("测试NER高亮功能")
    print("=" * 60)
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
            highlighted_text = result.get("高亮文本", [])
            entities = result.get("实体详情", [])
            
            print(f"\n识别到 {len(entities)} 个实体")
            print("实体详情:")
            for entity in entities:
                print(f"  - '{entity.get('识别实体', '')}' (分类: {entity.get('实体分类', 'N/A')})")
            
            print(f"\n高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"  {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')}, 置信度: {part.get('confidence', 0):.4f})")
                else:
                    print(f"  {i}. [普通] '{part.get('text', '')}'")
            
            print(f"\n完整高亮文本:")
            full_text = ""
            for part in highlighted_text:
                if part.get("highlight"):
                    full_text += f"[红色]{part.get('text', '')}[/红色]"
                else:
                    full_text += part.get("text", "")
            print(f"  {full_text}")
            
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_highlight_normalization():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("\n" + "="*60)
    print("测试标准化高亮功能")
    print("="*60)
    print(f"输入文本: {test_text}")
    
    try:
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
            highlighted_text = result.get("高亮文本", [])
            entities = result.get("实体详情", [])
            
            print(f"\n识别到 {len(entities)} 个实体")
            print("实体详情:")
            for entity in entities:
                print(f"  - '{entity.get('识别实体', '')}' (分类: {entity.get('实体分类', 'N/A')})")
            
            print(f"\n高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"  {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')}, 置信度: {part.get('confidence', 0):.4f})")
                else:
                    print(f"  {i}. [普通] '{part.get('text', '')}'")
            
            print(f"\n完整高亮文本:")
            full_text = ""
            for part in highlighted_text:
                if part.get("highlight"):
                    full_text += f"[红色]{part.get('text', '')}[/红色]"
                else:
                    full_text += part.get("text", "")
            print(f"  {full_text}")
            
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def test_simple_highlight():
    test_text = "A Round Financing"
    
    print("\n" + "="*60)
    print("测试简单案例高亮")
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
            highlighted_text = result.get("高亮文本", [])
            
            print(f"\n高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"  {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')})")
                else:
                    print(f"  {i}. [普通] '{part.get('text', '')}'")
            
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_highlight_ner()
    test_highlight_normalization()
    test_simple_highlight()
    print("\n测试完成！") 