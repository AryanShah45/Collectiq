# ---- Stage 1: build the React app ----
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (uses package.json; lockfile optional)
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps --no-audit --no-fund

# Build. Empty backend URL => the app calls "/api" on the same origin,
# which nginx forwards to the backend container.
COPY . .
ENV REACT_APP_BACKEND_URL="" \
    CI=false \
    GENERATE_SOURCEMAP=false
RUN npm run build

# ---- Stage 2: serve with nginx ----
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
