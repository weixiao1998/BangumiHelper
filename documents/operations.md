# 运维操作手册

## 操作 SQLite 数据库

数据库在容器内 `/app/data/bangumi.db`，运行时镜像无 sqlite3 CLI，用 Python 自带 sqlite3 模块执行。

**模板**（把 SQL 填进对应一行即可）：

```bash
docker compose exec -T backend python <<'EOF'
import sqlite3
c = sqlite3.connect('/app/data/bangumi.db')
print(c.execute("SQL").fetchall())   # 查询
c.execute("SQL"); c.commit()          # 写入
EOF
```

> 开发环境把 `docker compose` 换成 `docker compose -f docker-compose.yml -f docker-compose.dev.yml`。

### 核心 SQL

```sql
-- 番剧数量
SELECT COUNT(*) FROM bangumi;
-- 用户列表
SELECT id, username, is_admin FROM users;
-- 更换 MIKAN_URL 后更新历史域名（保留订阅，不丢数据）
UPDATE bangumi SET cover = REPLACE(cover, '旧域名', '新域名') WHERE cover LIKE '%旧域名%';
UPDATE episodes SET torrent_url = REPLACE(torrent_url, '旧域名', '新域名') WHERE torrent_url LIKE '%旧域名%';
-- 彻底清空番剧数据（级联删除订阅，谨慎）
DELETE FROM episodes; DELETE FROM subscriptions; DELETE FROM bangumi;
-- 运行时系统配置（正常用管理 UI「系统设置」修改，会自动失效缓存）
SELECT key, value FROM system_settings;
```

> 改完 `.env` 后需 `docker compose up -d` 重建容器使新环境变量生效（`restart` 不重读 .env）。
