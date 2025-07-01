import os
from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient

def get_client():
    url = os.getenv("WEAVIATE_URL", "http://infra-weaviate-1:8080")
    params = ConnectionParams.from_url(url, grpc_port=50051)
    client = WeaviateClient(params, skip_init_checks=True)
    client.connect()
    return client
