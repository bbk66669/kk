import os
from contextlib import contextmanager
from datetime import datetime

from weaviate.connect import ConnectionParams
from weaviate import WeaviateClient, exceptions as wexc
from weaviate.collections.classes.config import Property, DataType

# ------------ 运行时配置 ------------
BASE_URL  = os.getenv("WEAVIATE_URL", "http://infra-weaviate-1:8080")
GRPC_PORT = int(os.getenv("WEAVIATE_GRPC", 50051))
USE_GRPC  = bool(int(os.getenv("WEAVIATE_USE_GRPC", "1")))  # 1=启用 0=禁用
# -----------------------------------

@contextmanager
def weaviate_conn():
    params = ConnectionParams.from_url(
        BASE_URL,
        grpc_port=GRPC_PORT if USE_GRPC else None,
    )
    client = WeaviateClient(connection_params=params, skip_init_checks=True)
    client.connect()
    try:
        yield client
    finally:
        client.close()

def ensure_tradelog():
    with weaviate_conn() as client:
        if "TradeLog" in client.collections.list_all():
            print("ℹ️  TradeLog collection already exists, skipped.")
            return

        print(f"[{datetime.utcnow().isoformat()}] Creating TradeLog schema…")

        client.collections.create(
            name="TradeLog",
            description="策略交易与因果日志",
            properties=[
                Property(name="timestamp",    data_type=DataType.NUMBER),  # Unix ms
                Property(name="symbol",       data_type=DataType.TEXT),
                Property(name="signal",       data_type=DataType.TEXT),
                Property(name="price",        data_type=DataType.NUMBER),
                Property(name="size",         data_type=DataType.NUMBER),
                Property(name="stop",         data_type=DataType.NUMBER),
                Property(name="leverage",     data_type=DataType.NUMBER),
                Property(name="order_id",     data_type=DataType.TEXT),
                Property(name="order_status", data_type=DataType.TEXT),
                Property(name="prompt",       data_type=DataType.TEXT),
                Property(name="extra",        data_type=DataType.TEXT),
            ],
        )

        print("✅ TradeLog collection created.")

if __name__ == "__main__":
    try:
        ensure_tradelog()
    except wexc.WeaviateConnectionError as err:
        print("❌ 无法连接 Weaviate：", err)
    except wexc.WeaviateInvalidInputError as err:
        print("❌ Schema 创建失败：", err)
