import os
import time
import atexit
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient

_client = None

def get_client():
    global _client
    if _client is None:
        url = os.getenv("WEAVIATE_URL", "http://infra-weaviate-1:8080")
        params = ConnectionParams.from_url(url, grpc_port=50051)

        max_attempts = 10
        for i in range(max_attempts):
            try:
                client = WeaviateClient(params, skip_init_checks=True)
                client.connect()
                # 可选校验 readiness（需要 weaviate-client ≥4.6）
                if not client.is_ready():  # 或者 schema.get()，看你 prefer 哪个
                    raise RuntimeError("Weaviate not ready")
                _client = client
                atexit.register(_client.close)
                break
            except Exception as e:
                print(f"[Retry {i+1}/{max_attempts}] Weaviate connect failed: {e}")
                time.sleep(3)
        else:
            raise RuntimeError("Weaviate is not reachable after retries.")
    return _client