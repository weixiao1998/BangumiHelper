# 开发指南

## 新增数据源检查清单

1. 在 `services/data_sources/` 下新建文件，继承 `BaseDataSource`
2. 实现抽象方法：
   - `fetch_bangumi_calendar` - 获取番剧日历
   - `fetch_single_bangumi` - 获取单个番剧详情
   - `fetch_episode_of_bangumi` - 获取番剧剧集列表
   - `search_by_keyword` - 按关键词搜索
3. 时间解析：使用 `beijing_to_utc()` 将数据源时间转为 UTC（如果数据源是北京时间）
4. 在 `services/data_sources/__init__.py` 的 `DATA_SOURCES` 字典中注册
5. 如需新数据库字段：创建 Alembic 迁移
   ```bash
   alembic revision --autogenerate -m "description"
   bash migrate.sh upgrade
   ```
6. 更新 `schemas/schemas.py` 如需新 schema

## 新增下载器检查清单

1. 在 `services/downloaders/` 下新建文件，继承 `BaseDownloader`
2. 实现抽象方法：
   - `add_torrent` - 添加种子文件
   - `add_magnet` - 添加磁力链接
   - `get_torrents` - 获取任务列表
   - `remove_torrent` - 删除任务
3. 在 `services/downloaders/__init__.py` 的 `DOWNLOADERS` 字典中注册
4. 如需新数据库字段：创建 Alembic 迁移
5. 更新 `schemas/schemas.py` 如需新 schema

## 时间处理规范

- 后端统一使用 UTC 时间存储和传输
- 数据源解析时间后，使用 `app/core/utils.py` 中的工具函数转换：
  - `utc_now()` - 获取当前 UTC 时间
  - `beijing_to_utc(dt)` - 北京时间转 UTC
- 前端使用 `dayjs.utc(time).local().format()` 转为用户本地时间显示
