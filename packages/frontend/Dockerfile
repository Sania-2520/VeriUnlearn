# ─── Build Stage ────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies (full install; next is required to build)
COPY package.json package-lock.json ./
RUN npm ci

# Build the application
COPY . .
RUN npm run build

# ─── Runtime Stage ─────────────────────────────────────────
FROM node:22-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production

RUN addgroup -S veriunlearn && adduser -S veriunlearn -G veriunlearn

# Copy only what is needed to run the production server
COPY --from=builder --chown=veriunlearn:veriunlearn /app/.next ./.next
COPY --from=builder --chown=veriunlearn:veriunlearn /app/public ./public
COPY --from=builder --chown=veriunlearn:veriunlearn /app/package.json ./package.json
COPY --from=builder --chown=veriunlearn:veriunlearn /app/next.config.js ./
COPY --from=builder --chown=veriunlearn:veriunlearn /app/node_modules ./node_modules

USER veriunlearn

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:3000 >/dev/null 2>&1 || exit 1

CMD ["npm", "start"]
