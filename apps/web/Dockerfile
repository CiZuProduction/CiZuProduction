# ============================================================
# Frontend Next.js — Dockerfile (standalone output)
# Multi-stage build, non-root user
# Requires: output: "standalone" di next.config.mjs
# ============================================================

# ── Stage 1: install dependencies ─────────────────────────────────────────
FROM node:22-alpine AS deps

WORKDIR /app

# Salin package files saja dulu untuk cache layer
COPY package*.json ./

RUN npm install --legacy-peer-deps --prefer-offline

# ── Stage 2: build ────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time env — nilai ini akan ter-embed di bundle, JANGAN taruh secret
ARG NEXT_PUBLIC_API_BASE_URL=/api
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm run build

# ── Stage 3: runtime ──────────────────────────────────────────────────────
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Salin artefak standalone dari builder
COPY --from=builder --chown=node:node /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

# Jalankan sebagai non-root
USER node

EXPOSE 3000

# Gunakan node untuk healthcheck — wget tidak ada di alpine standalone
HEALTHCHECK --interval=20s --timeout=10s --start-period=60s --retries=5 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/', (r) => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
