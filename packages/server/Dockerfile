FROM python:3.11-slim

# 安装 LibreOffice（公式重算必需）与常用字体
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libreoffice-calc \
       fonts-wqy-zenhei \
       fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖元数据，利用缓存层
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e "."

# 再复制应用代码
COPY . .

# 确保上传目录存在
RUN mkdir -p /app/data/uploads

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
