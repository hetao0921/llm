from pymilvus import connections, utility

# Milvus连接参数
_HOST = '10.128.15.221'
_PORT = '19530'  # gRPC 端口

def check_milvus_grpc():
    try:
        # 连接到Milvus（使用gRPC）
        connections.connect(host=_HOST, port=_PORT)
        print("成功连接到Milvus via gRPC")
        
        # 检查是否支持多数据库功能
        if hasattr(utility, 'list_database'):
            databases = utility.list_database()
            print(f"现有数据库: {databases}")
        else:
            print("当前Milvus版本不支持多数据库功能")
            
    except Exception as e:
        print(f"操作失败: {e}")

if __name__ == '__main__':
    check_milvus_grpc()