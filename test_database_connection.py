#!/usr/bin/env python3
"""
测试数据库连接和表创建
"""

import os
import logging
from sqlalchemy import create_engine, text

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 数据库连接配置
DB_URL = "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/rag_learn"

def test_database_connection():
    """测试数据库连接"""
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            # 测试连接
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            logging.info(f"✅ 数据库连接测试成功: {test_value}")
            
            # 检查数据库
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            logging.info(f"📊 当前数据库: {db_name}")
            
            return True
            
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return False

def create_evaluation_metrics_table():
    """创建evaluation_metrics表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS evaluation_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        question TEXT NOT NULL COMMENT '问题内容',
        rag_retrieval_data JSON COMMENT 'RAG检索结果数据',
        gold_standard_data JSON COMMENT '黄金标准数据',
        execution_accuracy DECIMAL(5,4) COMMENT '执行准确率',
        exact_match_rate DECIMAL(5,4) COMMENT '精确匹配率',
        component_match_rate DECIMAL(5,4) COMMENT '组件匹配率 / SQL-F1值',
        retrieval_relevance DECIMAL(5,4) COMMENT '检索相关性',
        context_utilization DECIMAL(5,4) COMMENT '生成器上下文利用度',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG系统评估指标表'
    """
    
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            # 创建表
            conn.execute(text(create_table_sql))
            conn.commit()
            logging.info("✅ evaluation_metrics表创建成功或已存在")
            
            # 验证表是否存在
            result = conn.execute(text("SHOW TABLES LIKE 'evaluation_metrics'"))
            if result.fetchone():
                logging.info("✅ evaluation_metrics表确认存在")
                
                # 显示表结构
                result = conn.execute(text("DESCRIBE evaluation_metrics"))
                columns = result.fetchall()
                logging.info("📋 表结构:")
                for column in columns:
                    logging.info(f"  - {column[0]} ({column[1]})")
                
                return True
            else:
                logging.error("❌ evaluation_metrics表不存在")
                return False
                
    except Exception as e:
        logging.error(f"❌ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_insert_data():
    """测试插入数据"""
    try:
        engine = create_engine(DB_URL)
        
        # 测试数据
        test_data = {
            'question': '测试问题',
            'rag_retrieval_data': '{"test": "data"}',
            'gold_standard_data': '{"test": "gold"}',
            'execution_accuracy': 0.8500,
            'exact_match_rate': 0.9000,
            'component_match_rate': 0.8750,
            'retrieval_relevance': 0.9200,
            'context_utilization': 0.8800
        }
        
        insert_sql = """
        INSERT INTO evaluation_metrics (
            question, rag_retrieval_data, gold_standard_data,
            execution_accuracy, exact_match_rate, component_match_rate,
            retrieval_relevance, context_utilization
        ) VALUES (
            :question, :rag_retrieval_data, :gold_standard_data,
            :execution_accuracy, :exact_match_rate, :component_match_rate,
            :retrieval_relevance, :context_utilization
        )
        """
        
        with engine.connect() as conn:
            # 插入测试数据
            conn.execute(text(insert_sql), test_data)
            conn.commit()
            logging.info("✅ 测试数据插入成功")
            
            # 验证插入
            result = conn.execute(text("SELECT COUNT(*) FROM evaluation_metrics"))
            count = result.fetchone()[0]
            logging.info(f"📊 当前表中记录数: {count}")
            
            # 查询最新插入的数据
            result = conn.execute(text("SELECT * FROM evaluation_metrics ORDER BY id DESC LIMIT 1"))
            latest_record = result.fetchone()
            if latest_record:
                logging.info(f"📋 最新记录: ID={latest_record[0]}, 问题={latest_record[1]}")
            
            return True
            
    except Exception as e:
        logging.error(f"❌ 测试插入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始测试数据库连接和表创建...")
    
    # 测试数据库连接
    if not test_database_connection():
        print("❌ 数据库连接失败，退出")
        exit(1)
    
    # 创建表
    if not create_evaluation_metrics_table():
        print("❌ 表创建失败，退出")
        exit(1)
    
    # 测试插入数据
    if not test_insert_data():
        print("❌ 数据插入测试失败")
        exit(1)
    
    print("✅ 所有测试通过！数据库配置正确。")
