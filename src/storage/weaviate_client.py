from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient

def get_client():
    # 建立 HTTP+gRPC 混合连接，其中 gRPC 指向 50051
    params = ConnectionParams.from_url(
        "http://localhost:8080",
        grpc_port=50051,  # 只保留 grpc_port
    )
    client = WeaviateClient(
        connection_params=params,
        skip_init_checks=True,
    )
    client.connect()
    return client
