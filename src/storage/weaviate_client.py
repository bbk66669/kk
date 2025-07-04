import os
import atexit
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient

_client = None

def get_client():
    global _client
    if _client is None:
        url = os.getenv("WEAVIATE_URL", "http://infra-weaviate-1:8080")
        params = ConnectionParams.from_url(url, grpc_port=50051)
        _client = WeaviateClient(params, skip_init_checks=True)
        _client.connect()
        # 注册进程退出时自动 close
        atexit.register(_client.close)
    return _client
