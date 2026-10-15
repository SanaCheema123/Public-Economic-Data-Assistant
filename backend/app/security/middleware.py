from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger("peda.http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_bytes:
            return JSONResponse({"detail": "Request is too large", "request_id": request_id}, status_code=413)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(json.dumps({"request_id": request_id, "path": request.url.path, "event": "unhandled_error"}))
            return JSONResponse({"detail": "Unexpected server error", "request_id": request_id}, status_code=500)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": elapsed,
        }))
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Small deployment-safe guard. Use Redis-backed limits for multi-replica production."""

    buckets: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        key = f"{ip}:{request.url.path.split('/')[1:3]}"
        now = time.monotonic()
        bucket = self.buckets[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Rate limit reached. Please try again shortly."}, status_code=429)
        bucket.append(now)
        return await call_next(request)
