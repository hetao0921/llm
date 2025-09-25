import requests
import json

def test_siliconflow_chat_completion():
    # 配置参数
    url = "https://api.siliconflow.cn/v1/chat/completions"
    token = "sk-cieanfgxijrnpjwcryoacvulkmddronmgetnogpblipjrwhn"  # 请替换为您的实际token
    model = "Qwen/QwQ-32B"
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 请求数据
    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "What opportunities and challenges will the Chinese large model industry face in 2025?"
            }
        ]
    }
    
    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            print("请求成功！")
            print("响应内容：")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # 提取模型回复
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0]['message']
                print(f"\n模型回复：{message['content']}")
        else:
            print(f"请求失败，状态码：{response.status_code}")
            print(f"错误信息：{response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"请求异常：{e}")
    except json.JSONDecodeError as e:
        print(f"JSON解析错误：{e}")

if __name__ == "__main__":
    test_siliconflow_chat_completion()