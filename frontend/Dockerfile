# syntax=docker/dockerfile:1

# ---- Dependencies ----
FROM node:26-alpine AS deps

WORKDIR /app

# Node 26 起发行版不再自带 corepack，先装上；pnpm 版本仍只由 package.json 的 packageManager 决定
RUN npm install -g corepack@0.35.0 && corepack enable

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
