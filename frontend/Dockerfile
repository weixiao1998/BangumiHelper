# syntax=docker/dockerfile:1

# ---- Dependencies ----
FROM node:24-alpine AS deps

WORKDIR /app

# pnpm 版本只在 package.json 的 packageManager 里声明，corepack 会自动按它下载
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm config set registry https://registry.npmmirror.com \
    && pnpm install --frozen-lockfile

# ---- Build ----
FROM deps AS builder

COPY . .
RUN pnpm build

# ---- Runtime ----
FROM caddy:2-alpine

COPY --from=builder /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80
EXPOSE 443

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
