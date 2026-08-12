"""FastAPI 应用入口。"""

import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APIError, APITimeoutError

from app.api.novel import router as novel_router
from app.api.projects import router as projects_router
from app.config import settings
from app.middleware import (
    RequestLogMiddleware,
    RequestSizeLimitMiddleware,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期钩子（预留：模型预热、数据库连接等）。"""
    logging.getLogger(__name__).info("AI 网文作者 Agent 启动完成")
    yield


app = FastAPI(
    title=settings.app_name,
    description="基于 DeepSeek API + RAG 的网络小说大纲生成系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：允许本地前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=settings.max_request_body_size,
)
app.add_middleware(RequestLogMiddleware)

app.include_router(novel_router)
app.include_router(projects_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局兜底：任何未捕获异常返回结构化错误，便于前端展示与排查。"""
    # DeepSeek 网络/API 异常单独处理：避免出现裸 500，提示可操作
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        logging.getLogger(__name__).error("DeepSeek 连接失败(全局兜底): %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "status": "error",
                "message": "无法连接到 DeepSeek API（网络不通或代理未配置）。请检查网络/代理后重试。",
            },
        )
    if isinstance(exc, APIError):
        logging.getLogger(__name__).error("DeepSeek API 错误(全局兜底): %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "status": "error",
                "message": f"DeepSeek API 返回错误：{exc}",
            },
        )
    request_id = uuid.uuid4().hex
    tb = traceback.format_exc()
    logging.getLogger(__name__).error(
        "未捕获异常 request_id=%s %s %s: %s\n%s",
        request_id,
        request.method,
        request.url.path,
        exc,
        tb,
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status": "error",
            "message": "后端处理请求时发生错误，请稍后重试。如需反馈，请提供请求 ID。",
            "detail": request_id,
        },
    )


@app.get("/api/health")
async def health_check() -> dict:
    """健康检查接口。"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_available": bool(settings.deepseek_api_key),
    }


if __name__ == "__main__":
    import os
    import uvicorn

    # 默认仅本机可访问；需要局域网访问时设置 ALLOW_LAN=0.0.0.0
    uvicorn.run(
        "app.main:app",
        host=os.getenv("ALLOW_LAN", "127.0.0.1"),
        port=8000,
        reload=True,
    )
