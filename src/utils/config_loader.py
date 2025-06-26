import os, yaml, pathlib, numbers, copy

def _deep_merge(a: dict, b: dict) -> dict:
    """递归地用 b 覆盖 a，返回新 dict"""
    out = copy.deepcopy(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

_CFG_CACHE = None
def load(path: str | pathlib.Path = "configs/config.yaml") -> dict:
    global _CFG_CACHE
    if _CFG_CACHE is not None:
        return _CFG_CACHE

    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    override = pathlib.Path("configs/config.override.yaml")
    if override.exists():
        with open(override, "r") as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})

    # 环境变量覆盖
    def _env_override(node: dict, prefix: str = ""):
        for k, v in node.items():
            env_key = (prefix + k).upper()
            if isinstance(v, dict):
                _env_override(v, env_key + "_")
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
    _env_override(cfg)

    _CFG_CACHE = cfg
    return cfg
