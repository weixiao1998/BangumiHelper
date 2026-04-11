# 运维操作手册

## 宿主机直接操作 SQLite 数据库

数据库存放在 Docker Volume，宿主机用 `sqlite3` 直接操作比写脚本进容器方便得多。

### 安装 sqlite3

```bash
apt-get install -y sqlite3
```

### 数据库路径

```bash
DB="/var/lib/docker/volumes/bangumihelper_bangumi-data/_data/bangumi.db"
```

> 注：路径取决于 Docker Compose 项目名。默认项目名为目录名 `bangumihelper`，Volume 名为 `bangumihelper_bangumi-data`。可用 `docker volume ls` 查看实际名称。

### 常用操作

```bash
# 查看表
sqlite3 "$DB" ".tables"

# 查看番剧数量
sqlite3 "$DB" "SELECT COUNT(*) FROM bangumi;"

# 清空旧数据（例如换 MIKAN_URL 后重新抓取）
sqlite3 "$DB" "DELETE FROM episodes; DELETE FROM subscriptions; DELETE FROM bangumi;"

# 查看用户
sqlite3 "$DB" "SELECT id, username, is_admin FROM users;"
```
