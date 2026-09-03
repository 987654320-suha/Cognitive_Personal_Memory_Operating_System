# ðŸ“ LOCATION: backend/app/middleware/logging_middleware.py
"""
logging_middleware.py
=====================
Request/response logging middleware for FastAPI.
Logs: method, path, status code, response time.
Also tracks slow requests (>2s) for performance monitoring.
"""

from __future__ import annotations
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("CogniSphere")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s â€” %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

SLOW_REQUEST_THRESHOLD_SECONDS = 2.0


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(
                f"ERROR {request.method} {request.url.path} "
                f"â€” {type(e).__name__}: {e} ({elapsed:.3f}s)"
            )
            raise

        elapsed = time.perf_counter() - start
        status  = response.status_code

        log_fn = logger.warning if elapsed > SLOW_REQUEST_THRESHOLD_SECONDS else logger.info
        log_fn(
            f"{request.method:6} {request.url.path:<45} "
            f"â†’ {status} ({elapsed:.3f}s)"
            + (" [SLOW]" if elapsed > SLOW_REQUEST_THRESHOLD_SECONDS else "")
        )

        # Attach timing header for frontend debugging
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        return response


