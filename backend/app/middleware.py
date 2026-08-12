"""自定义 ASGI 中间件。

- RequestSizeLimitMiddleware：限制 HTTP 请求体大小，防止超大 JSON 打满内存/磁盘；
- RequestLogMiddleware：请求级日志（request_id / method / path / status / 耗时），
  并回写 X-Request-Id 响应头。
"""

import logging
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    """限制 HTTP 请求体大小，防止超大 JSON 打满内存/磁盘。"""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.max_bytes <= 0:
            await self.app(scope, receive, send)
            return

        # 快速路径：Content-Length 已超限时直接拒绝，避免读取请求体
        content_length = 0
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    content_length = 0
                break
        if content_length > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        # 缓冲并计数请求体：超限立即拒绝，未超限则重放给应用，
        # 避免 FastAPI 解析 body 时吞掉异常导致无法返回 413。
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        body_bytes = bytes(body)
        delivered = False

        async def replay_receive() -> dict:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            # 请求体重放完成后，后续 receive 委托给原始 receive：
            # 流式响应阶段 Starlette 会用它监听客户端断开，
            # 不能直接返回 http.disconnect（会被误判为客户端已断开）。
            return await receive()

        await self.app(scope, replay_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        """返回 413 响应，不继续读取请求体。"""
        response = JSONResponse(
            status_code=413,
            content={
                "success": False,
                "status": "error",
                "message": f"请求体过大（超过 {self.max_bytes} 字节限制）。",
            },
        )
        await response(scope, receive, send)


class RequestLogMiddleware:
    """请求级日志：request_id / method / path / status / 耗时，并回写 X-Request-Id 响应头。"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        status = 0

        async def send_wrapper(message: dict) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request_id=%s method=%s path=%s status=%d duration_ms=%.0f",
                request_id,
                scope.get("method", ""),
                scope.get("path", ""),
                status,
                duration_ms,
            )
