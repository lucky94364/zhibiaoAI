# backend

当前状态：目录与开发约定已建立，尚未创建可运行后端。

技术基线：Python 3.11、FastAPI、Pydantic、SQLAlchemy、Alembic，依赖使用 uv 管理。先单 worker 与 SQLite，保留 PostgreSQL 和对象存储适配。

阅读：[架构](../docs/current/01_系统架构与目录规范.md)、[数据与状态](../docs/current/02_数据模型与状态机.md)、[API](../docs/current/03_API与接口契约.md)、[分阶段任务](../docs/current/07_AI分步开发与执行提示.md)。

文件、数据、任务和版本逻辑写入本目录。运行数据存根目录 var，读取根 .env；真实 API 协议需验证后接入，默认 mock 必须明示。

S01—S02 后在本文件记录实际安装、迁移、API/worker启动和测试命令。当前没有 app 包和 pyproject，启动命令尚不可执行。
