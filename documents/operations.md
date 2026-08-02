# 运维操作手册

## 操作 MySQL 数据库

数据存储在 compose 中的 `db` 服务（MySQL 8.0），用 `mysql` CLI 直接在 db 容器内执行。

**模板**（把 SQL 填进 `-e` 即可）：

```bash
# 查询
docker compose exec -T db mysql -ubangumi -pbangumi bangumi -e "SQL"
# 写入
docker compose exec -T db mysql -ubangumi -pbangumi bangumi -e "SQL"
```

> 开发环境把 `docker compose` 换成 `docker compose -f docker-compose.yml -f docker-compose.dev.yml`。
> `-p` 与密码之间无空格（MySQL CLI 限制）。密码取自 `.env` 中的 `DB_PASSWORD`，若已修改请替换命令中的 `bangumi`。

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

### 备份与恢复

```bash
# 备份（导出到宿主机当前目录）
docker compose exec -T db mysqldump -ubangumi -pbangumi bangumi > bangumi_backup.sql

# 恢复
docker compose exec -T db mysql -ubangumi -pbangumi bangumi < bangumi_backup.sql
```

> 改完 `.env` 后需 `docker compose up -d` 重建容器使新环境变量生效（`restart` 不重读 .env）。
