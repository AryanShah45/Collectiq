# CollectIQ — all-in-one image (frontend + backend in one service).
# Used for single-service hosting like Render. The backend serves the built
# React app on the same origin as the /api routes, so there are no cross-origin
# cookie/CORS concerns.
#
# Local development still uses docker-compose.yml (separate frontend + backend).

# ---------- Stage 1: build the React frontend ----------
FROM node:20-bullseye AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* frontend/yarn.lock* ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
# Empty backend URL => the app calls /api on its own origin (served by the backend below)
ENV REACT_APP_BACKEND_URL=""
ENV CI=false
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# ---------- Stage 2: python backend that also serves the build ----------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/static

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ .
# Bring in the compiled frontend so the API can serve it at "/"
COPY --from=frontend /fe/build /app/static

EXPOSE 8001
# Render injects $PORT; defaults to 8001 locally.
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}
