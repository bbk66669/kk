import hashlib, redis, os, json, time

_redis = redis.Redis(host=os.getenv("REDIS_HOST","localhost"),
                     port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)

TTL_SEC = int(os.getenv("INTENT_TTL","120"))

def _key(intent: dict)->str:
    h = hashlib.sha1(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    return f"intent:{h}"

def hit_or_set(intent: dict) -> bool:
    k = _key(intent)
    if _redis.exists(k):
        return True
    _redis.setex(k, TTL_SEC, int(time.time()))
    return False
