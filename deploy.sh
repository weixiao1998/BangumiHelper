#!/bin/bash

set -e

echo "=== BangumiHelper 部署脚本 ==="

if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件配置你的参数"
    echo "特别是 SECRET_KEY 和 CORS_ORIGINS_STR"
    exit 1
fi

echo "构建并启动服务..."
docker compose up -d --build

echo ""
echo "=== 部署完成 ==="
echo "服务已启动，监听端口 8081"
echo ""
echo "下一步："
echo "  1. 配置宿主机反向代理（Nginx/Caddy），将域名转发到 localhost:8081"
echo "  2. 如需 HTTPS，在宿主机反向代理中配置 TLS 证书"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "  重启服务: docker compose restart"
