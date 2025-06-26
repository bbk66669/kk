# ----------------------------------------------------------------------
# OKX-SWAP 规格查询 & 行情工具
#   - 60 s 本地缓存，打印 hit/失效
#   - 自动处理 minSz / lotSz 为小数时的取整
# ----------------------------------------------------------------------
import time, math, requests, pandas as pd

_OKX_REST = "https://www.okx.com"
_CACHE: dict[tuple, tuple[float, dict]] = {}          # key -> (timestamp, spec)

# ---------- REST helpers ----------
def _fetch_instrument_raw(symbol: str) -> dict:
    """面值 ctVal / minSz / lotSz / …"""
    inst_type = "SWAP"
    uly = "-".join(symbol.split("-")[:2])              # ETH-USDT-SWAP → ETH-USDT
    url = f"{_OKX_REST}/api/v5/public/instruments?instType={inst_type}&uly={uly}"
    js = requests.get(url, timeout=4).json()
    for it in js.get("data", []):
        if it["instId"] == symbol:
            return it
    raise RuntimeError(f"instrument not found: {symbol}")

def _fetch_candles(symbol: str, bar: str = "1m", limit: int = 30) -> pd.DataFrame:
    """最近 N 根 K 线（按时间升序）"""
    url = f"{_OKX_REST}/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}"
    data = requests.get(url, timeout=4).json().get("data", [])
    df = pd.DataFrame(
        data, columns=["ts", "o", "h", "l", "c", "vol", "volCcy", "volCcyQuote", "confirm"]
    ).astype({"o": float, "h": float, "l": float, "c": float})
    return df.iloc[::-1].reset_index(drop=True)

# ---------- main ----------
def get_instrument_spec(
    symbol: str,
    *,
    bar: str = "1m",
    limit: int = 30,
    cache_seconds: int = 60,
) -> dict:
    """
    返回 dict 字段：
      ct_val, min_sz, lot_sz, period_sec,
      recent_prices, recent_high, recent_low
    """
    key = (symbol, bar, limit)
    now = time.time()

    # 1. cache
    ts_cached, spec_cached = _CACHE.get(key, (0, None))
    hit = spec_cached and now - ts_cached < cache_seconds
    print(f"[spec-cache] {symbol} hit={bool(hit)} ts={int(ts_cached)} now={int(now)}")
    if hit:
        return spec_cached

    # 2. pull fresh
    try:
        raw = _fetch_instrument_raw(symbol)
        df = _fetch_candles(symbol, bar, limit)
        ct_val = float(raw["ctVal"])
        # minSz / lotSz 可能是 "0.01" → 转成 float
        min_sz = math.ceil(float(raw["minSz"]))
        lot_sz = float(raw["lotSz"])  # 保留小数，不转 int
        spec = {
            "ct_val": ct_val,
            "min_sz": min_sz,
            "lot_sz": lot_sz,
            "period_sec": 60,
            "recent_prices": df["c"],
            "recent_high": df["h"],
            "recent_low": df["l"],
        }
    except Exception as e:
        print("⚠️  get_instrument_spec 拉取失败，用默认值:", e)
        spec = {
            "ct_val": 0.01,
            "min_sz": 1,
            "lot_sz": 1,
            "period_sec": 60,
            "recent_prices": pd.Series([0]),
            "recent_high": pd.Series([0]),
            "recent_low": pd.Series([0]),
        }

    # 3. store cache
    _CACHE[key] = (now, spec)
    return spec

# ----------------------------------------------------------------------
# 简易 ticker
# ----------------------------------------------------------------------
def get_latest_price(symbol: str) -> float:
    url = f"{_OKX_REST}/api/v5/market/ticker?instId={symbol}"
    try:
        r = requests.get(url, timeout=4).json()
        return float(r["data"][0]["last"])
    except Exception as e:
        print("⚠️  获取最新价格失败:", e)
        return 0.0
# ----------------------------------------------------------------------
