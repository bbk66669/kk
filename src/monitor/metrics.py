from prometheus_client import (
    Counter, Histogram, Gauge, start_http_server, REGISTRY
)

# ── helpers ────────────────────────────────────────────────
def _counter(name, doc, labels=None):
    try:                                         # 已注册 → 直接复用
        return REGISTRY._names_to_collectors[name]     # type: ignore
    except KeyError:
        return Counter(name, doc, labels or [])

# metrics HTTP 端口可能已由 ws_main.py 启动，捕获异常即可
try:
    start_http_server(8000, addr="0.0.0.0")
except OSError:
    pass

# ── 通用指标 ───────────────────────────────────────────────
gpt_requests_total    = _counter("gpt_requests_total",   "Total GPT calls")
okx_orders_total      = _counter("okx_orders_total",     "OKX orders", ["side"])
okx_fees_usdt_total   = _counter("okx_fees_usdt_total",  "Accumulated OKX fees (USDT)")

gpt_latency_seconds    = Histogram("gpt_latency_seconds",   "GPT latency (s)")
order_latency_seconds  = Histogram("order_latency_seconds", "OKX order latency (s)")

equity_usdt            = Gauge("equity_usdt", "Account equity (USDT)")

# NEW – 本地 Trailing-SL 触发次数
trailing_stop_hits_total = _counter("trailing_stop_hits_total",
                                    "Local trailing-stop triggered")
