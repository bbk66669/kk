import hashlib, redis, os, json, time

# 默认用 windking-net 内部服务名
_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_redis     = redis.from_url(_REDIS_URL)

TTL_SEC = int(os.getenv("INTENT_TTL", "120"))    # 可用环境变量覆盖

def _key(intent: dict) -> str:
    """intent dict → sha1 key"""
    h = hashlib.sha1(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    return f"intent:{h}"

def hit_or_set(intent: dict) -> bool:
    k = _key(intent)
    if _redis.exists(k):
        return True
    _redis.setex(k, TTL_SEC, int(time.time()))
    return False
