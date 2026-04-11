#!/bin/bash

set -e

echo "=== 数据库迁移 ==="

cd /app

case "$1" in
    "upgrade")
        echo "升级数据库到最新版本..."
        alembic upgrade head
        ;;
    "downgrade")
        echo "回滚一个版本..."
        alembic downgrade -1
        ;;
    "history")
        echo "迁移历史:"
        alembic history
        ;;
    "current")
        echo "当前版本:"
        alembic current
        ;;
    *)
        echo "用法: $0 {upgrade|downgrade|history|current}"
        exit 1
        ;;
esac
