FROM python:3.10-slim

WORKDIR /app

# ① 先装依赖，利用 layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ② 再复制全部源码
COPY . .

CMD ["python", "-u", "ws_main.py"]
