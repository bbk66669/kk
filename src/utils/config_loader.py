import os, yaml, pathlib, numbers

_CFG_CACHE = None
def load(path: str | pathlib.Path = "configs/config.yaml") -> dict:
    global _CFG_CACHE
    if _CFG_CACHE is not None:
        return _CFG_CACHE

    # 1. 先读主配置
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    # 2. 再试着读灰度覆盖（如果存在就合并）
    override_path = pathlib.Path("configs/config.override.yaml")
    if override_path.exists():
        with open(override_path, "r") as f:
            override = yaml.safe_load(f) or {}
        from utils import deep_merge
        cfg = deep_merge(cfg, override)

    # 环境变量覆盖逻辑（保持不变）
    def _override(node: dict, prefix: str = ""):
        for k, v in node.items():
            env_key = (prefix + k).upper()
            if isinstance(v, dict):
                _override(v, env_key + "_")
            else:
                ev = os.getenv(env_key)
                if ev is not None:
                    if isinstance(v, bool):
                        node[k] = ev.lower() in ("1", "true", "yes")
                    elif isinstance(v, numbers.Integral):
                        node[k] = int(ev)
                    elif isinstance(v, numbers.Real):
                        node[k] = float(ev)
                    else:
                        node[k] = ev
    _override(cfg)

    _CFG_CACHE = cfg
    return cfg
