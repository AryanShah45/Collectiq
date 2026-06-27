# CollectIQ backend — FastAPI + Uvicorn
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8001

# Serve the API. Render injects $PORT; locally it defaults to 8001.
# MONGO_URL, DB_NAME, JWT_SECRET, etc. come from the environment.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}
