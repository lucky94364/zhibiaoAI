# backend

S01—S02 已实现工程骨架、11 张业务表、项目 CRUD（创建/查询/更新）、持久任务与独立串行 worker。未实现文件处理、OCR、AI 或核验业务。

本机 Python：`/opt/anaconda3/bin/python3.11`（3.11.7），依赖由 uv.lock 锁定。uv 0.13.8 本次装在临时目录 `/private/tmp/zb-uv/bin/uv`；普通终端需要先安装 uv 并加入 PATH，也可将下述 uv 替换为该绝对路径。

从项目根进入 backend：

```sh
cd backend
uv sync --frozen --python /opt/anaconda3/bin/python3.11
uv run --frozen pytest -q
uv run --frozen alembic upgrade head
uv run --frozen alembic current
uv run --frozen alembic check
uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

若 8000 占用可改为 `--port 8001`。接口包括 health/capabilities、GET/POST /api/v1/projects、GET/PATCH /api/v1/projects/{id}、GET /api/v1/jobs/{id}、POST /api/v1/jobs/{id}/retry。OpenAPI `/openapi.json`，交互文档 `/docs`；只暴露已实现路径。完整设计仍在 docs/current/contracts。

配置自动加载根 `.env`（可复制 `.env.example`），环境变量优先。相对存储与 SQLite 路径以项目根解析，密钥用 SecretStr，响应不返回配置或密钥。CORS 逗号分隔。

capabilities 的 storage 为临时文件写读探测，database 为连接与 SELECT 1 探测，不代表业务持久层已完成。解析、OCR、转换和 workflow_api 当前均 unavailable，即使填入密钥也不会伪称适配已完成；mock 仅标记所选配置，未实现模拟工作流。

Alembic 当前 head 为 `0001_s02`，包含 11 张业务表及索引。API 不自动建表，请先迁移。运行数据在根 var/，不进入版本库。

另一个终端从 backend 运行：

```sh
uv run --frozen python -m app.tasks.worker
# 运维检查：恢复 300 秒无心跳的 running 任务后退出
uv run --frozen python -m app.tasks.worker --recover-only
# 恢复后最多领取一个任务
uv run --frozen python -m app.tasks.worker --once
# 临时端口 HTTP 创建/更新/重启验证，使用 var/s02_http_smoke.db 独立库
uv run --frozen python scripts/smoke_s02.py
```

任务由后续阶段的业务服务通过 JobStore.enqueue 创建，本阶段不开放任意任务提交 API。worker 当前无业务处理器；领取任务会明确失败 JOB_HANDLER_UNAVAILABLE，不伪造成功。5 秒心跳，过期任务转 interrupted，必须明确重试；不会自动重放。重试保留原任务与输入，生成 parent_job_id/attempt，旧 claim token 无法再提交。当前只支持单串行 worker。

写 API 必须提供非空 Idempotency-Key；X-Actor-Id 为本机操作标签。项目 PATCH 必须携带 expected_input_revision；context/scope 是完整对象替换，不是字段合并。内容变化递增输入版本、清空当前核验指针并退回 preparing，历史记录不改；仅改名称不递增业务输入版本。相同幂等键返回原始响应，同键异体或更换操作者返回 409。context.deadline 必须带偏移并以 UTC 存储，timezone 必须为有效 IANA 名称，截止日期由后端按该时区派生。

项目创建的幂等键全局唯一，PATCH 按项目和操作隔离，任务键按项目隔离。为了保持 11 张业务表，项目内部 operation_records_json 保存幂等结果，不额外增加业务表；当前适合试点规模，后续大规模使用再迁移独立账本。perform_once 支持在同一短事务内保护数据库副作用及幂等结果，不能把文件/网络写入当作数据库事务；相应文件副作用检查点在 S03/S09 实现。

已验证 SQLite；PostgreSQL 驱动与事务测试未运行。JSON 列中的多值来源归属及 review 的多态目标归属需要各后续业务服务校验，不能仅靠外键。当前快照只有表和类型，不生成或发布核验结果。
