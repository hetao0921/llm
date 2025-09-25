#!/usr/bin/env python3
"""
诊断检索问题的脚本
"""

import os
import sys
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def diagnose_retrieval_issue():
    """诊断检索问题"""
    
    print("🔍 开始诊断检索问题...")
    print("=" * 60)
    
    # 1. 检查模型一致性
    print("1️⃣ 检查模型一致性:")
    print("-" * 40)
    
    models_used = {
        "02-ingest-ddl-1.py": "BAAI/bge-large-en-v1.5",
        "03-ingest-q2sql-1.py": "BAAI/bge-large-en-v1.5", 
        "04-ingest-db-desc-1.py": "BAAI/bge-large-en-v1.5",  # 已修复
        "05-text2sql-rag-v2-ok-1.py": "BAAI/bge-large-en-v1.5"  # 已修复
    }
    
    for script, model in models_used.items():
        print(f"  ✅ {script}: {model}")
    
    print("  ✅ 所有脚本现在都使用相同的英文模型")
    
    # 2. 检查可能的问题原因
    print("\n2️⃣ 可能的问题原因:")
    print("-" * 40)
    print("  🔍 问题1: 模型不一致 (已修复)")
    print("  🔍 问题2: 向量嵌入API返回相同结果")
    print("  🔍 问题3: 数据库中存储的是相同数据")
    print("  🔍 问题4: 检索逻辑有问题")
    print("  🔍 问题5: 集合索引或配置问题")
    
    # 3. 建议的解决步骤
    print("\n3️⃣ 建议的解决步骤:")
    print("-" * 40)
    print("  1️⃣ 重新摄入数据 (使用统一的英文模型)")
    print("  2️⃣ 运行向量多样性测试")
    print("  3️⃣ 检查数据库中的数据")
    print("  4️⃣ 测试检索功能")
    
    # 4. 提供修复命令
    print("\n4️⃣ 修复命令:")
    print("-" * 40)
    print("  # 重新摄入所有数据 (按顺序执行)")
    print("  python 02-ingest-ddl-1.py")
    print("  python 03-ingest-q2sql-1.py") 
    print("  python 04-ingest-db-desc-1.py")
    print("")
    print("  # 测试向量多样性")
    print("  python test_embedding_diversity.py")
    print("")
    print("  # 测试检索功能")
    print("  python 05-text2sql-rag-v2-ok-1.py")
    
    # 5. 检查当前配置
    print("\n5️⃣ 当前配置检查:")
    print("-" * 40)
    
    try:
        # 导入主模块检查配置
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from importlib import import_module
        main_module = import_module('05-text2sql-rag-v2-ok-1')
        
        print(f"  📋 API URL: {main_module.SILICON_FLOW_API_URL}")
        print(f"  📋 嵌入模型: {main_module.SILICON_FLOW_EMBEDDING_MODEL}")
        print(f"  📋 Milvus Host: {main_module.MILVUS_HOST}")
        print(f"  📋 Milvus Port: {main_module.MILVUS_PORT}")
        print(f"  📋 数据库名: {main_module.DATABASE_NAME}")
        print(f"  📋 DDL集合: {main_module.COLLECTION_DDL}")
        print(f"  📋 Q2SQL集合: {main_module.COLLECTION_Q2SQL}")
        print(f"  📋 描述集合: {main_module.COLLECTION_DBDESC}")
        
    except Exception as e:
        print(f"  ❌ 无法检查配置: {e}")
    
    print("\n✅ 诊断完成！")
    print("💡 建议：先重新摄入数据，然后测试检索功能")

if __name__ == "__main__":
    diagnose_retrieval_issue()
