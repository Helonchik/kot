from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import structlog
import asyncio

from app.core.settings import settings
from app.api import api_router
from app.api.dashboard import router as dashboard_router

logger = structlog.get_logger()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Dashboard and API for Discord Role Manager Pro",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="app/dashboard/static"), name="static")

    app.include_router(api_router, prefix="/api")
    app.include_router(dashboard_router)

    @app.on_event("startup")
    async def startup_event():
        from app.core.database import init_db
        await init_db()
        logger.info("api_startup", project=settings.PROJECT_NAME)
        # Uncomment below if you want the API to automatically launch the bot in the same process
        # asyncio.create_task(run_bot())

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("api_shutdown")

    return app

app = create_app()

async def run_bot():
    from app.bot.bot import RoleManagerBot
    bot = RoleManagerBot()
    await bot.start(settings.DISCORD_BOT_TOKEN)
