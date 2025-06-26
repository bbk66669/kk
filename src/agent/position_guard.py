import json, os, asyncio, logging, time
from typing import Literal, Optional

Signal = Literal["BUY", "SELL", "HOLD", None]

class PositionGuard:
    """
    持仓方向本地缓存（单向持仓）。
    * 线程安全 + 过期自动失效
    """
    _instance: Optional['PositionGuard'] = None
    _lock     = asyncio.Lock()

    def __new__(cls, *a, **k):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -------- #
    def __init__(
        self,
        *,
        cache_file: str = "/tmp/position_guard.json",
        expire_sec: float = 3600.0,
        logger: logging.Logger | None = None,
    ) -> None:
        if hasattr(self, "_init"):  # 保证单例只初始化一次
            return
        self._init = True
        self.file = cache_file
        self.expire = expire_sec
        self.log = logger or logging.getLogger("PositionGuard")
        self.state: dict[str, str | float] = {"direction": None, "ts": 0.0}
        self._load()

    # -------- public -------- #
    async def get(self) -> Signal:
        async with self._lock:
            self._check_expire()
            return self.state["direction"]  # type: ignore

    async def update(self, direction: Signal) -> None:
        async with self._lock:
            self.state.update(direction=direction, ts=time.time())
            self._save()

    async def reset(self) -> None:
        await self.update(None)

    # -------- private -------- #
    def _check_expire(self) -> None:
        if self.state["direction"] and time.time() - self.state["ts"] > self.expire:
            self.log.info("Position expired, auto-reset.")
            self.state.update(direction=None, ts=0.0)
            self._save()

    def _load(self) -> None:
        try:
            if os.path.exists(self.file):
                with open(self.file, "r") as f:
                    self.state = json.load(f)
        except Exception as e:
            self.log.warning("load cache failed: %s, reset.", e)
            self.state = {"direction": None, "ts": 0.0}

    def _save(self) -> None:
        try:
            with open(self.file, "w") as f:
                json.dump(self.state, f)
        except Exception as e:
            self.log.warning("save cache failed: %s", e)
