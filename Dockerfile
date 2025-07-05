FROM python:3.10-slim
WORKDIR /app

# 1. 安装命令行依赖（curl、jq、sed、coreutils）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl jq sed coreutils && \
    rm -rf /var/lib/apt/lists/*

# 2. 拷贝 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 补丁（你的 sed 替换）
RUN sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/okxclient.py \
 && sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/CopyTrading.py \
 && sed -i 's/, *proxy=proxy//g; s/ *proxy=proxy//g' /usr/local/lib/python3.10/site-packages/okx/Account.py

# 4. 拷贝你的代码
COPY . .

ENTRYPOINT ["python", "-u", "ws_main.py"]
