import time, collections
from typing import Deque, Literal

Signal = Literal["BUY", "SELL", "HOLD"]

class SignalFilter:
    """
    连续同向信号/节流滤波。
    """
    def __init__(self, *, n_same: int = 2, throttle: float = 30.0) -> None:
        self.n_same = n_same
        self.throttle = throttle
        self._buf: Deque[Signal] = collections.deque(maxlen=n_same)
        self._last_emit_ts: float = 0.0

    def push(self, sig: Signal) -> Signal | None:
        now = time.time()
        if now - self._last_emit_ts < self.throttle:
            return None  # 节流
        if sig == "HOLD":
            self._buf.clear()
            return None
        self._buf.append(sig)
        if len(self._buf) == self.n_same and len(set(self._buf)) == 1:
            self._buf.clear()
            self._last_emit_ts = now
            return sig
        return None

    def reset(self) -> None:
        self._buf.clear()
        self._last_emit_ts = 0.0
