import collections, statistics, time

class EventClassifier:
    """窗口内价格与量能特征 → bool 显著事件"""
    def __init__(self,
        price_window=60, vol_window=30,
        pct_th=0.004, accel_th=2.0, vol_th=3.0):
        self.prices = collections.deque(maxlen=price_window)
        self.vols   = collections.deque(maxlen=vol_window)
        self.pct_th      = pct_th
        self.accel_th    = accel_th
        self.vol_th_ratio= vol_th
        self.last_ts = 0

    def push(self, price: float, volume: float = 1.0) -> bool:
        now = time.time()
        self.prices.append(price)
        self.vols.append(volume)
        # 1) 价差
        if len(self.prices) >= 2:
            pct = abs(price - self.prices[-2]) / self.prices[-2]
            if pct >= self.pct_th: return True
        # 2) 加速度
        if len(self.prices) >= 3:
            accel = (self.prices[-1]-self.prices[-2])-(self.prices[-2]-self.prices[-3])
            mu = statistics.mean(abs(self.prices[i]-self.prices[i-1]) for i in range(1,len(self.prices)))
            if mu and abs(accel)/mu >= self.accel_th: return True
        # 3) 量能
        if len(self.vols) == self.vols.maxlen:
            if volume / (sum(self.vols)/len(self.vols)) >= self.vol_th_ratio:
                return True
        # fallback
        return False
