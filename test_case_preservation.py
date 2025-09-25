#!/usr/bin/env python3
"""
Test script to verify case preservation in financial term NER
"""

import requests
import json

def test_ner_case_preservation():
    """Test that NER preserves original case and spacing"""
    
    # Test cases with different case patterns
    test_cases = [
        "A Round Financing",
        "a round financing", 
        "A ROUND FINANCING",
        "a Round Financing",
        "A round financing",
        "My company has A Round Financing",
        "The company completed A Round Financing last year",
        "We are looking for A Round Financing opportunities"
    ]
    
    print("Testing Financial Term NER Case Preservation")
    print("=" * 50)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{test_text}'")
        
        # Test NER endpoint
        try:
            response = requests.post(
                "http://localhost:8000/finterm/ner",
                json={
                    "text": test_text,
                    "classifications": ["L"]  # Financing category
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("实体详情", [])
                
                if entities:
                    print(f"  ✓ NER found {len(entities)} entities:")
                    for entity in entities:
                        original_term = entity.get("原始单词", "")
                        recognized_term = entity.get("识别实体", "")
                        print(f"    - Original: '{original_term}'")
                        print(f"    - Recognized: '{recognized_term}'")
                        print(f"    - Category: {entity.get('实体分类', 'N/A')}")
                        print(f"    - Score: {entity.get('识别分数', 'N/A')}")
                        
                        # Check if case is preserved
                        if original_term == recognized_term:
                            print(f"    ✓ Case preserved correctly")
                        else:
                            print(f"    ✗ Case mismatch: '{original_term}' vs '{recognized_term}'")
                else:
                    print(f"  ✗ No entities found")
            else:
                print(f"  ✗ NER request failed: {response.status_code}")
                print(f"    Response: {response.text}")
                
        except Exception as e:
            print(f"  ✗ NER test failed: {e}")
        
        # Test normalization endpoint
        try:
            response = requests.post(
                "http://localhost:8000/finterm/normalize",
                json={
                    "text": test_text,
                    "classifications": ["L"],  # Financing category
                    "collection_name": "my_finterm_collection"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entities = result.get("实体详情", [])
                
                if entities:
                    print(f"  ✓ Normalization found {len(entities)} entities:")
                    for entity in entities:
                        original_term = entity.get("识别实体", "")
                        normalized_term = entity.get("标准化术语", "")
                        print(f"    - Original: '{original_term}'")
                        print(f"    - Normalized: '{normalized_term}'")
                        print(f"    - Category: {entity.get('实体分类', 'N/A')}")
                        print(f"    - Score: {entity.get('匹配的标准化术语准确度', 'N/A')}")
                        
                        # Check if case is preserved
                        if original_term == normalized_term:
                            print(f"    ✓ Case preserved in normalization")
                        else:
                            print(f"    ✗ Case mismatch in normalization: '{original_term}' vs '{normalized_term}'")
                else:
                    print(f"  ✗ No entities found in normalization")
            else:
                print(f"  ✗ Normalization request failed: {response.status_code}")
                print(f"    Response: {response.text}")
                
        except Exception as e:
            print(f"  ✗ Normalization test failed: {e}")

def test_specific_case():
    """Test the specific case mentioned by the user"""
    test_text = "my company has a A-share."
    
    print(f"\nTesting specific case: '{test_text}'")
    print("=" * 50)
    
    try:
        response = requests.post(
            "http://localhost:8000/finterm/ner",
            json={
                "text": test_text,
                "classifications": ["E"]  # Equities category for A-share
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("实体详情", [])
            
            if entities:
                print(f"✓ Found {len(entities)} entities:")
                for entity in entities:
                    print(f"  - '{entity.get('识别实体', '')}' (Category: {entity.get('实体分类', 'N/A')})")
            else:
                print("✗ No entities found")
        else:
            print(f"✗ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Test failed: {e}")

if __name__ == "__main__":
    print("Financial Term NER Case Preservation Test")
    print("Make sure the backend server is running on localhost:8000")
    print()
    
    test_ner_case_preservation()
    test_specific_case()
    
    print("\nTest completed!") 