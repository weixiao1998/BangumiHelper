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
-- 订阅组列表（含暂停状态）
SELECT id, user_id, name, status FROM subscription_groups ORDER BY user_id, id;
-- 每个组的订阅数
SELECT g.id, g.name, COUNT(s.id) AS subscriptions
FROM subscription_groups g LEFT JOIN subscriptions s ON s.group_id = g.id
GROUP BY g.id, g.name ORDER BY g.id;
-- 更换 MIKAN_URL 后更新历史域名（保留订阅，不丢数据）
UPDATE bangumi SET cover = REPLACE(cover, '旧域名', '新域名') WHERE cover LIKE '%旧域名%';
UPDATE episodes SET torrent_url = REPLACE(torrent_url, '旧域名', '新域名') WHERE torrent_url LIKE '%旧域名%';
-- 彻底清空番剧数据（级联删除订阅，谨慎）
DELETE FROM episodes; DELETE FROM subscriptions; DELETE FROM bangumi;
-- 运行时系统配置（正常用管理 UI「系统设置」修改，会自动失效缓存）
SELECT key, value FROM system_settings;
```

> 查询/写入含中文的组名时，建议在 `mysql` 命令中加 `--default-character-set=utf8mb4`，
> 否则 `WHERE name='默认订阅组'` 这类字面量可能因连接字符集不匹配而查不到。

### 迁移 014 前置清理（重要）

014 把订阅改为「订阅组」结构，并删除 `global_filters` 与 `subscriptions.rss_token`。
本迁移**不做任何回填**，要求升级前这三张表无业务数据：

```sql
DELETE FROM bangumi_filters;
DELETE FROM subscriptions;
DELETE FROM global_filters;
```

清理后再重启/升级后端（`main.py` 启动时自动 `alembic upgrade head`）。
迁移会为每个已有用户初始化一个空的「默认订阅组」；新注册用户也会自动创建默认组。
如果跳过清理直接升级，`subscriptions.group_id` 非空列会添加失败。

### 备份与恢复

```bash
# 备份（导出到宿主机当前目录）
docker compose exec -T db mysqldump -ubangumi -pbangumi bangumi > bangumi_backup.sql

# 恢复
docker compose exec -T db mysql -ubangumi -pbangumi bangumi < bangumi_backup.sql
```

> 改完 `.env` 后需 `docker compose up -d` 重建容器使新环境变量生效（`restart` 不重读 .env）。
