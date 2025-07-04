FROM python:3.10-slim
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 补丁：删除 OKX SDK 源码里所有 proxy=proxy 的传参
RUN sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/okxclient.py \
 && sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/CopyTrading.py \
 && sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/Account.py

# 拷代码
COPY . .

ENTRYPOINT ["python", "-u", "ws_main.py"]
