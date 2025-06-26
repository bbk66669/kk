import logging
import weaviate

# TradeLog schema 定义
_SCHEMA = {
    "class": "TradeLog",
    "description": "策略交易与因果日志",
    "properties": [
        {"name": "timestamp",    "dataType": ["number"]},
        {"name": "symbol",       "dataType": ["text"]},
        {"name": "signal",       "dataType": ["text"]},
        {"name": "price",        "dataType": ["number"]},
        {"name": "size",         "dataType": ["number"]},
        {"name": "leverage",     "dataType": ["number"]},
        {"name": "order_id",     "dataType": ["text"]},
        {"name": "status",       "dataType": ["text"]},
        {"name": "prompt",       "dataType": ["text"]},
        {"name": "extra",        "dataType": ["text"]},
        {"name": "pnl_realized", "dataType": ["number"]},
        {"name": "equity",       "dataType": ["number"]},
    ],
}

def get_client():
    return weaviate.connect_to_custom(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
    )

def ensure_schema():
    client = None
    try:
        client = get_client()
        # v4 客户端中要通过 schema_api 访问 schema 接口
        schema = client.schema_api.get()
        classes = [c["class"] for c in schema.get("classes", [])]

        if "TradeLog" not in classes:
            client.schema_api.create_class(_SCHEMA)
            logging.info("Weaviate: created TradeLog class")
        else:
            trade_cls = next(c for c in schema["classes"] if c["class"] == "TradeLog")
            existing = {p["name"] for p in trade_cls.get("properties", [])}
            for prop in _SCHEMA["properties"]:
                if prop["name"] not in existing:
                    client.schema_api.add_property("TradeLog", prop)
                    logging.info(f"Weaviate: added property '{prop['name']}' to TradeLog")
    except Exception as e:
        logging.warning(f"Weaviate schema ensure failed: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    ensure_schema()
