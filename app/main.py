from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.redis import close_redis

OUTPUTS_DIR = Path("outputs")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/api/v1")

    # Serve rendered videos at /outputs/video/<job_id>.mp4
    OUTPUTS_DIR.mkdir(exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

    return app


app = create_app()
