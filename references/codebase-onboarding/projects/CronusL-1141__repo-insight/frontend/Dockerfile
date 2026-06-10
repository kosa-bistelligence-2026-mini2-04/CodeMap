# syntax=docker/dockerfile:1.7
# RepoInsight frontend image — Vite build → nginx static serve

ARG NODE_VERSION=20.18.1
ARG NGINX_VERSION=1.27.3

############################
# Stage 1: builder
############################
FROM node:${NODE_VERSION}-bookworm-slim AS builder

ENV PNPM_HOME=/usr/local/share/pnpm \
    PATH=/usr/local/share/pnpm:$PATH \
    CI=1

RUN corepack enable \
 && corepack prepare pnpm@9.12.3 --activate

WORKDIR /build

# Lockfile-aware caching
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# Source
COPY . .

# Production build
RUN pnpm run build

############################
# Stage 2: nginx runtime
############################
FROM nginx:${NGINX_VERSION}-alpine AS runtime

# Add curl for healthcheck
RUN apk add --no-cache curl \
 && addgroup -S -g 1001 app \
 && adduser  -S -u 1001 -G app app

# Replace default config
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets
COPY --from=builder /build/dist /usr/share/nginx/html

# nginx needs write access to runtime dirs as non-root
RUN chown -R app:app /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \
 && touch /var/run/nginx.pid \
 && chown app:app /var/run/nginx.pid

USER app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
