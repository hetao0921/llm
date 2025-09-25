#!/usr/bin/env python3
"""
Text2SQL RAG 生成器
负责读取检索结果，调用大模型生成SQL，并执行SQL查询
"""

import os
import logging
import re
import requests
import json
from dotenv import load_dotenv

# 尝试导入 SQLAlchemy，如果失败则提供明确的错误信息
try:
    from sqlalchemy import create_engine, text
except ImportError as e:
    print("错误: 缺少必要的依赖包，请执行以下命令安装：")
    print("pip install sqlalchemy pymysql requests python-dotenv")
    raise e

# 1. 环境与日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()  # 加载 .env 环境变量

# 2. Silicon Flow 配置
SILICON_FLOW_API_URL = "https://api.siliconflow.cn/v1"
SILICON_FLOW_API_TOKEN = os.getenv("SILICON_FLOW_API_TOKEN", "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn")
SILICON_FLOW_CHAT_MODEL = os.getenv("SILICON_FLOW_CHAT_MODEL", "Qwen/QwQ-32B")

# 3. 数据库配置
DB_URL = os.getenv(
    "SAKILA_DB_URL", 
    "mysql+pymysql://root:Rzx#1218@10.128.15.5:3306/sakila"
)

# 4. Silicon Flow 聊天补全函数
def siliconflow_chat_completion(messages: list, temperature: float = 0.1) -> str:
    """使用 Silicon Flow 聊天补全接口"""
    try:
        url = f"{SILICON_FLOW_API_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {SILICON_FLOW_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": SILICON_FLOW_CHAT_MODEL,
            "messages": messages,
            "temperature": temperature
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']
                content = message['content'].strip()
                logging.info("✅ Silicon Flow 聊天补全调用成功")
                return content
            else:
                logging.error("❌ 响应中没有找到有效的回复内容")
                return None
        else:
            logging.error(f"❌ Silicon Flow 聊天 API 请求失败，状态码: {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"❌ 聊天补全异常: {e}")
        return None

# 5. SQL 提取函数
def extract_sql(text: str) -> str:
    """从文本中提取 SQL 语句"""
    if not text:
        return ""
    
    # 尝试匹配 SQL 代码块
    sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL)
    if sql_blocks:
        return sql_blocks[0].strip()
    
    # 如果没有找到代码块，尝试匹配 SELECT 语句
    select_match = re.search(r'SELECT.*?;', text, re.DOTALL)
    if select_match:
        return select_match.group(0).strip()
    
    # 尝试匹配 UPDATE 语句
    update_match = re.search(r'UPDATE.*?;', text, re.DOTALL)
    if update_match:
        return update_match.group(0).strip()
    
    # 尝试匹配 INSERT 语句  
    insert_match = re.search(r'INSERT.*?;', text, re.DOTALL)
    if insert_match:
        return insert_match.group(0).strip()
        
    # 尝试匹配 DELETE 语句
    delete_match = re.search(r'DELETE.*?;', text, re.DOTALL)
    if delete_match:
        return delete_match.group(0).strip()
    
    # 如果都没有找到，返回原始文本
    return text.strip()

# 6. 测试数据库连接
def test_database_connection():
    """测试数据库连接是否正常"""
    try:
        # 检查是否安装了 pymysql
        try:
            import pymysql
        except ImportError:
            print("❌ 未安装 pymysql，请执行: pip install pymysql")
            return False
            
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # 执行一个简单的测试查询
            result = conn.execute(text("SELECT 1"))
            test_result = result.scalar()
            if test_result == 1:
                logging.info("✅ 数据库连接测试成功")
                return True
            else:
                logging.error("❌ 数据库连接测试失败")
                return False
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return False

# 7. 执行 SQL 查询
def execute_sql_query(sql: str):
    """执行 SQL 查询并返回结果"""
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            # 判断 SQL 类型
            sql_upper = sql.upper().strip()
            
            if sql_upper.startswith('SELECT'):
                # 查询语句
                result = conn.execute(text(sql))
                cols = result.keys()
                rows = result.fetchall()
                
                print("\n" + "="*60)
                print("📊 查询结果：")
                print("="*60)
                print(f"📋 列名: {cols}")
                print("-" * 60)
                for i, r in enumerate(rows, 1):
                    print(f"{i}. {r}")
                print("="*60)
                print(f"✅ 总计: {len(rows)} 条记录")
                
            elif sql_upper.startswith(('UPDATE', 'INSERT', 'DELETE')):
                # DML 语句
                result = conn.execute(text(sql))
                conn.commit()  # 提交事务
                affected_rows = result.rowcount
                
                print("\n" + "="*60)
                print("✅ SQL 执行成功")
                print("="*60)
                print(f"📋 执行的SQL: {sql}")
                print(f"📊 影响的行数: {affected_rows}")
                print("="*60)
                
            else:
                # 其他类型的 SQL
                result = conn.execute(text(sql))
                conn.commit()
                print(f"✅ SQL 执行完成: {sql}")
                
    except Exception as e:
        logging.error(f"[执行] 执行失败: {e}")
        print(f"❌ 执行错误：{e}")

# 8. 从检索结果生成SQL
def generate_sql_from_retrieval(question: str, ddl_context: str, desc_context: str, example_context: str = ""):
    """基于检索结果生成SQL"""
    print(f"\n🔍 处理查询: {question}")
    
    # 显示检索到的上下文信息
    print(f"\n📊 检索上下文总结:")
    print("=" * 60)
    print(f"📋 DDL结构信息: {len(ddl_context)} 字符")
    print(f"📋 问答示例: {len(example_context)} 字符") 
    print(f"📋 字段描述: {len(desc_context)} 字符")
    print("=" * 60)
    
    # 显示实际检索到的内容片段
    print(f"\n🔍 实际检索内容预览:")
    print("-" * 60)
    print(f"📋 DDL内容前200字符: {ddl_context[:200]}...")
    print(f"📋 问答内容前200字符: {example_context[:200]}...")
    print(f"📋 描述内容前200字符: {desc_context[:200]}...")
    print("-" * 60)
    
    # Prompt 组装
    system_prompt = """你是一个专业的SQL生成助手。请根据提供的数据库结构、字段描述和示例，将自然语言查询转换为准确的SQL语句。

请严格遵循以下要求：
1. 只返回SQL语句，不要包含任何解释或说明
2. 确保SQL语法正确
3. 使用提供的表名和字段名
4. 如果问题涉及日期范围，请使用合适的日期函数
5. 如果需要连接多个表，请确保连接条件正确
6. 注意：Sakila数据库中的演员表是actor，不是actors"""

    user_prompt = (
        f"### 数据库结构定义:\n{ddl_context}\n\n"
        f"### 字段描述:\n{desc_context}\n\n"
        f"### 示例查询:\n{example_context}\n\n"
        f"### 用户查询:\n{question}\n\n"
        f"请生成对应的SQL查询语句："
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print("🤖 正在生成SQL...")

    # 调用 Silicon Flow 聊天补全接口
    raw_sql = siliconflow_chat_completion(messages, temperature=0.1)
    
    if raw_sql is None:
        print("❌ SQL生成失败")
        return None
        
    sql = extract_sql(raw_sql)
    logging.info(f"[生成] 原始输出: {raw_sql}")
    logging.info(f"[生成] 提取的SQL: {sql}")

    if not sql:
        print("❌ 未能提取到有效的SQL语句")
        return None

    print(f"📋 生成的SQL: {sql}")
    return sql

# 9. 从文件读取检索结果并生成SQL
def process_retrieval_results_file(file_path: str):
    """从检索结果文件读取数据并生成SQL"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析文件内容
        sections = content.split("=" * 80)
        results = []
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.strip().split('\n')
            if len(lines) < 10:  # 确保有足够的内容
                continue
                
            question = ""
            standard_answer = ""
            ddl_results = ""
            desc_results = ""
            ddl_count = 0
            desc_count = 0
            
            current_field = ""
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("问题:"):
                    question = line.replace("问题:", "").strip()
                elif line.startswith("标准答案:"):
                    standard_answer = line.replace("标准答案:", "").strip()
                elif line.startswith("DDL返回结果:"):
                    current_field = "ddl"
                    content_lines = []
                elif line.startswith("数据库描述返回结果:"):
                    current_field = "desc"
                    content_lines = []
                elif line.startswith("DDL统计:"):
                    ddl_count = int(line.replace("DDL统计:", "").strip())
                elif line.startswith("数据库描述统计:"):
                    desc_count = int(line.replace("数据库描述统计:", "").strip())
                elif line.startswith("-" * 40):
                    if current_field == "ddl":
                        ddl_results = "\n".join(content_lines)
                    elif current_field == "desc":
                        desc_results = "\n".join(content_lines)
                    current_field = ""
                    content_lines = []
                elif current_field and line:
                    content_lines.append(line)
            
            if question and ddl_results and desc_results:
                results.append({
                    "question": question,
                    "standard_answer": standard_answer,
                    "ddl_results": ddl_results,
                    "desc_results": desc_results,
                    "ddl_count": ddl_count,
                    "desc_count": desc_count
                })
        
        print(f"📋 从文件读取到 {len(results)} 个检索结果")
        return results
        
    except Exception as e:
        print(f"❌ 读取检索结果文件失败: {e}")
        return []

# 10. 批量生成SQL
def batch_generate_sql(retrieval_results: list, output_file: str = "generation_results.txt"):
    """批量生成SQL并输出到文件"""
    results = []
    
    print(f"🚀 开始批量生成SQL，共 {len(retrieval_results)} 个问题...")
    
    for i, item in enumerate(retrieval_results, 1):
        question = item["question"]
        ddl_context = item["ddl_results"]
        desc_context = item["desc_results"]
        standard_answer = item["standard_answer"]
        
        print(f"\n处理第 {i}/{len(retrieval_results)} 个问题...")
        print(f"问题: {question}")
        
        # 生成SQL
        generated_sql = generate_sql_from_retrieval(question, ddl_context, desc_context)
        
        if generated_sql:
            results.append({
                "question": question,
                "standard_answer": standard_answer,
                "generated_sql": generated_sql,
                "ddl_count": item["ddl_count"],
                "desc_count": item["desc_count"]
            })
            
            # 执行SQL（可选）
            try:
                print(f"🔍 执行生成的SQL...")
                execute_sql_query(generated_sql)
            except Exception as e:
                print(f"⚠️ SQL执行失败: {e}")
        else:
            print(f"❌ 第 {i} 个问题SQL生成失败")
    
    # 输出结果到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write("=" * 80 + "\n")
            f.write(f"问题: {result['question']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"标准答案: {result['standard_answer']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"生成的SQL: {result['generated_sql']}\n")
            f.write("-" * 40 + "\n")
            f.write(f"DDL统计: {result['ddl_count']}\n")
            f.write(f"描述统计: {result['desc_count']}\n")
            f.write("=" * 80 + "\n\n")
    
    print(f"\n✅ 批量生成完成！")
    print(f"📄 结果已保存到: {output_file}")
    
    return results

# 11. 程序入口
if __name__ == "__main__":
    print("🚀 Text2SQL RAG 生成器启动中...")
    
    # 检查依赖
    print("📦 检查依赖包...")
    try:
        import sqlalchemy
        import requests
        # 特别检查 pymysql
        try:
            import pymysql
            print("✅ pymysql 已安装")
        except ImportError:
            print("❌ 未安装 pymysql，请执行: pip install pymysql")
            exit(1)
        print("✅ 所有依赖包检查通过")
    except ImportError as e:
        print("❌ 缺少依赖包，请执行以下命令安装：")
        print("pip install sqlalchemy pymysql requests python-dotenv")
        exit(1)
    
    # 测试数据库连接
    print("🔗 测试数据库连接...")
    if not test_database_connection():
        print("❌ 数据库连接测试失败")
        exit(1)
    
    print("✅ 生成器初始化完成！")
    
    try:
        while True:
            print("\n" + "="*60)
            print("请选择操作模式：")
            print("1. 单个问题生成SQL")
            print("2. 从检索结果文件批量生成SQL")
            print("3. 退出")
            
            choice = input("请输入选择 (1/2/3): ").strip()
            
            if choice == "1":
                # 单个问题生成
                question = input("💬 请输入自然语言查询: ").strip()
                if question:
                    # 这里需要用户手动输入检索结果，或者从文件读取
                    ddl_context = input("📋 请输入DDL上下文 (或按回车跳过): ").strip()
                    desc_context = input("📋 请输入描述上下文 (或按回车跳过): ").strip()
                    example_context = input("📋 请输入示例上下文 (或按回车跳过): ").strip()
                    
                    sql = generate_sql_from_retrieval(question, ddl_context, desc_context, example_context)
                    if sql:
                        try:
                            execute_sql_query(sql)
                        except Exception as e:
                            print(f"⚠️ SQL执行失败: {e}")
                else:
                    print("❌ 输入不能为空")
                    
            elif choice == "2":
                # 从文件批量生成
                file_path = input("📄 请输入检索结果文件路径 (默认: F:\\llm\\code\\rag-new-project001\\data\\retrieval_results.txt): ").strip()
                if not file_path:
                    file_path = "F:\\llm\\code\\rag-new-project001\\data\\retrieval_results.txt"
                
                retrieval_results = process_retrieval_results_file(file_path)
                if retrieval_results:
                    output_file = "F:\\llm\\code\\rag-new-project001\\data\\generation_results.txt"
                    results = batch_generate_sql(retrieval_results, output_file)
                else:
                    print("❌ 无法读取检索结果文件")
                    
            elif choice == "3":
                print("👋 感谢使用，再见！")
                break
            else:
                print("❌ 无效选择，请重新输入")
                
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        logging.error(f"程序执行异常: {e}")
        print(f"❌ 程序异常: {e}")
