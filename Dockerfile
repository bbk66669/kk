FROM python:3.10-slim

WORKDIR /app

# 装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷代码（包含 src/、configs/、ws_main.py 等）
COPY . .

# 默认启动
CMD ["python", "-u", "ws_main.py"]
