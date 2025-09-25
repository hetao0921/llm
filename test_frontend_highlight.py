#!/usr/bin/env python3
"""
测试前端高亮功能
"""

import requests
import json

def test_frontend_highlight():
    test_text = "During A Round Financing, a startup evaluated its options against benchmarks like the ABA Bank Index and potential A-Share listing prospects."
    
    print("测试前端高亮功能")
    print("=" * 60)
    print(f"输入文本: {test_text}")
    
    try:
        # 测试NER服务
        print("\n1. 测试NER服务高亮数据:")
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
            
            print(f"  高亮文本片段数: {len(highlighted_text)}")
            print("  高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"    {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')})")
                else:
                    print(f"    {i}. [普通] '{part.get('text', '')}'")
            
            # 检查是否有高亮部分
            highlight_parts = [part for part in highlighted_text if part.get("highlight")]
            if highlight_parts:
                print(f"  ✓ 包含 {len(highlight_parts)} 个高亮部分")
            else:
                print(f"  ✗ 没有高亮部分")
        else:
            print(f"  ✗ NER请求失败: {response.status_code}")
        
        # 测试标准化服务
        print("\n2. 测试标准化服务高亮数据:")
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
            
            print(f"  高亮文本片段数: {len(highlighted_text)}")
            print("  高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"    {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')})")
                else:
                    print(f"    {i}. [普通] '{part.get('text', '')}'")
            
            # 检查是否有高亮部分
            highlight_parts = [part for part in highlighted_text if part.get("highlight")]
            if highlight_parts:
                print(f"  ✓ 包含 {len(highlight_parts)} 个高亮部分")
            else:
                print(f"  ✗ 没有高亮部分")
        else:
            print(f"  ✗ 标准化请求失败: {response.status_code}")
            
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
            
            print(f"高亮文本片段数: {len(highlighted_text)}")
            print("高亮文本结构:")
            for i, part in enumerate(highlighted_text):
                if part.get("highlight"):
                    print(f"  {i}. [高亮] '{part.get('text', '')}' (类型: {part.get('entity_type', 'N/A')})")
                else:
                    print(f"  {i}. [普通] '{part.get('text', '')}'")
            
            # 检查是否有高亮部分
            highlight_parts = [part for part in highlighted_text if part.get("highlight")]
            if highlight_parts:
                print(f"✓ 包含 {len(highlight_parts)} 个高亮部分")
            else:
                print(f"✗ 没有高亮部分")
        else:
            print(f"✗ 请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")

if __name__ == "__main__":
    test_frontend_highlight()
    test_simple_highlight()
    print("\n测试完成！")
    print("\n前端高亮说明:")
    print("1. 后端已提供高亮数据结构")
    print("2. 前端已修改为使用后端高亮数据")
    print("3. 识别出的实体应该显示为红色粗体")
    print("4. 鼠标悬停可查看实体类型和置信度") 