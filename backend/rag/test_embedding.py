import requests
import json

# 配置参数
API_URL = "https://api.siliconflow.cn/v1/embeddings"
API_TOKEN = "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn"  # 替换为你的实际API令牌

# 请求头
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 请求数据
payload = {
    "model": "BAAI/bge-large-zh-v1.5",
    "input": "Silicon flow embedding online: fast, affordable, and high-quality embedding services. come try it out!"
}

# 发送请求
response = requests.post(API_URL, headers=headers, json=payload)

# 检查响应
if response.status_code == 200:
    result = response.json()
    # 提取嵌入向量
    embedding = result['data'][0]['embedding']
    print("生成的向量维度:", len(embedding))
    print("前10维向量值:", embedding[:10])
    print("\n完整响应:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"请求失败，状态码: {response.status_code}")
    print("响应内容:", response.text)