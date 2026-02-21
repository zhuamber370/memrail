from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if not getattr(request.state, "request_id", ""):
            request.state.request_id = f"req_{uuid.uuid4().hex[:12]}"
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        expected = f"Bearer {self.api_key}"
        if auth != expected:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "invalid or missing api key",
                        "request_id": getattr(request.state, "request_id", ""),
                    }
                },
            )
        return await call_next(request)
