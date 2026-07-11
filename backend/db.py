import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

mongo_url = os.environ["MONGO_URL"]

# Local/no-server fallback: set MONGO_URL=memory to run against an in-memory
# MongoDB (mongomock_motor). Intended only for local dev/demo where no real
# MongoDB is reachable; production paths are unaffected.
if mongo_url == "memory":
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
    db = client[os.environ["DB_NAME"]]
else:
    client = None  # set below

# Connection options. For Atlas (TLS) we pin a known-good CA bundle via certifi,
# which avoids "SSL handshake" failures on minimal server images. We also give
# the driver a generous window to find the server, so a cluster that is just
# waking up doesn't immediately error.
_kwargs = {"serverSelectionTimeoutMS": 30000, "connectTimeoutMS": 30000}
if "mongodb+srv" in mongo_url or "mongodb.net" in mongo_url:
    try:
        import certifi
        _kwargs["tlsCAFile"] = certifi.where()
    except Exception:
        pass

if client is None:
    client = AsyncIOMotorClient(mongo_url, **_kwargs)
    db = client[os.environ["DB_NAME"]]
