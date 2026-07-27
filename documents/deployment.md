# Docker 生产部署

## 环境准备

宿主机需安装 Docker、Docker Compose、Caddy。

## 构建与启动

```bash
cp .env.example .env
# 修改 .env：SECRET_KEY 等（仅引导配置；运行时配置在管理 UI「系统设置」改）
docker compose up -d --build
```

镜像采用多阶段构建 + BuildKit 缓存挂载（uv / pnpm 依赖缓存），依赖不变时重建只跑代码拷贝层，速度很快。镜像已命名标签（`bangumi-helper-backend:latest` / `bangumi-helper-frontend:latest`），无代码变更时可直接 `docker compose up -d` 复用已有镜像。

> 开发调试请用开发模式（挂载源码 + 热重载），见 [development.md](development.md#docker-开发模式)。

容器运行后：
- frontend 暴露 `8081` → Caddy 容器内 80
- backend 暴露 `8000`（仅容器网络内访问）

## 宿主机 Caddy 反向代理

宿主机安装 Caddy，负责多域名和 HTTPS 证书自动申请：

```bash
apt-get install -y caddy

cat > /etc/caddy/Caddyfile << 'EOF'
example.com {
    reverse_proxy localhost:8081
}
EOF

systemctl reload caddy
```

- 宿主机 Caddy 监听 80/443，自动申请 Let's Encrypt。
- 容器内的 Caddy 仅做静态文件托管和 `/api/*` 反代到 backend，端口映射 `8081:80`。
- 如需使用子域名，替换为 `bgm.example.com` 等即可。

## 修改 .env 后重启

```bash
# 重启 backend 使新环境变量生效（不重建镜像）
docker compose restart backend

# 如改动了 Dockerfile 或依赖，需要重建
docker compose up -d --build backend
```
