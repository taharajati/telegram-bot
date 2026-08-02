FROM node:20-alpine AS base

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

FROM base AS deps

COPY package.json package-lock.json* ./
RUN npm install --include=dev

FROM base AS builder

# ── JWT_SECRET must be available at build time for Edge middleware ──
ARG JWT_SECRET
ENV JWT_SECRET=${JWT_SECRET:?"JWT_SECRET must be set at build time"}

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner

ENV NODE_ENV=production
# Also set at runtime for API routes (Node.js)
ARG JWT_SECRET
ENV JWT_SECRET=${JWT_SECRET:?"JWT_SECRET must be set at build time"}

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
