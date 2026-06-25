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
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.meetings.create_index("id", unique=True)
    await db.meetings.create_index("meeting_date")
    await seed_users()
    await seed_meetings()
    logger.info("Startup complete: indexes ensured, users & meetings seeded.")


@app.on_event("shutdown")
async def shutdown():
    client.close()
