import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from db import db, client
from auth import auth_router, users_router, seed_users
from routes_meetings import meetings_router
from routes_settings import settings_router, seed_settings
from routes_notion import notion_router
from seed_data import seed_meetings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Meeting Insights API")


@app.get("/api/")
async def root():
    return {"message": "Meeting Insights API is running"}


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(meetings_router)
app.include_router(settings_router)
app.include_router(notion_router)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    import asyncio

    async def _init_db():
        await db.users.create_index("email", unique=True)
        await db.login_attempts.create_index("identifier")
        await db.meetings.create_index("id", unique=True)
        await db.meetings.create_index("meeting_date")
        await db.extract_jobs.create_index("created_dt", expireAfterSeconds=86400)
        await seed_users()
        await seed_settings()
        await seed_meetings()

    # Retry for a while so a database that is still waking up (e.g. a free-tier
    # cluster resuming) doesn't crash the app. If it's still unreachable, keep
    # serving anyway — the port opens, and it self-heals once the DB is back.
    for attempt in range(1, 11):
        try:
            await _init_db()
            logger.info("Startup complete: indexes ensured, users & settings seeded.")
            return
        except Exception as exc:
            logger.warning("Database not ready (attempt %d/10): %s", attempt, exc)
            await asyncio.sleep(6)
    logger.error("Could not reach the database during startup; the app will keep "
                 "running and connect once the database is available.")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# --- Optionally serve the built frontend from this same service (single-origin deploy) ---
# Enabled only when a static directory exists (e.g. the all-in-one Docker image used for
# Render). For the local docker-compose setup the frontend is served separately by nginx,
# so this directory is absent and the API runs API-only.
_static_dir = os.environ.get("STATIC_DIR", "/app/static")
if os.path.isdir(_static_dir):
    from starlette.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")
    logger.info("Serving frontend from %s", _static_dir)
