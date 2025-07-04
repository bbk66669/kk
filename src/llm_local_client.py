import requests, logging, functools, asyncio, time, os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://infra-ollama-1:11434/api/generate")
MODEL      = "gemma:2b-instruct-q4_K_M"    # ← 如果要换模型，只改这里

def _call_ollama(prompt: str, temperature=0.2, read_timeout=300):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "temperature": temperature,
        "stream": False
    }
    t0 = time.time()
    try:
        # 10s 连接超时，300s 读取超时
        r = requests.post(OLLAMA_URL, json=payload, timeout=(10, read_timeout))
        r.raise_for_status()
        resp = r.json().get("response", "ERR")
    except Exception as e:
        logging.warning("Ollama timeout/err: %s", e)
        resp = "ERR"
    return resp, time.time() - t0

async def ask_local_llm(prompt: str, temperature=0.2):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, functools.partial(_call_ollama, prompt, temperature)
    )
