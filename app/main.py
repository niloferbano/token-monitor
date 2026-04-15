from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.api import router as quota_router


class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_upload_size:
                return Response(content="Body too large", status_code=413)

        return await call_next(request)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Token Monitor",
        description="LLM token usage monitoring and quota enforcement service.",
        version="0.1.0",
    )

    application.add_middleware(LimitUploadSize, max_upload_size=1_000_000)
    application.include_router(quota_router)

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)