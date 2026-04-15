from fastapi import FastAPI

from app.core.api import router as quota_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Token Monitor",
        description="LLM token usage monitoring and quota enforcement service.",
        version="0.1.0",
    )

    application.include_router(quota_router)

    @application.get("/", tags=["meta"])
    async def read_root() -> dict[str, str]:
        return {"service": "token-monitor", "status": "ok"}

    @application.get("/health", tags=["meta"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
