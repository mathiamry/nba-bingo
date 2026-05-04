# Multi-stage build : Python génère le JSON, Node build le SPA, Nginx sert.

# === Stage 1 : génération de game.json ===
FROM python:3.11-slim AS data-gen
WORKDIR /app
COPY nba_bingo_grid.py nba_dataset_loader.py ./
COPY nba_dataset_extracted ./nba_dataset_extracted
RUN python nba_bingo_grid.py

# === Stage 2 : build du frontend Vue ===
FROM node:20-alpine AS frontend-build
ARG VITE_PARTYKIT_HOST=127.0.0.1:1999
ENV VITE_PARTYKIT_HOST=$VITE_PARTYKIT_HOST
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY --from=data-gen /app/frontend/public/game.json ./public/game.json
RUN npm run build

# === Stage 3 : runtime Nginx ===
FROM nginx:alpine AS runtime
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
