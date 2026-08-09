# AI 网文作者 Agent - 后端镜像
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/knowledge ./knowledge
COPY backend/.env.example ./.env.example

# 当前生成流程按板块直接读取知识库 txt，无需构建向量索引
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000"]
