# backend

S01 已实现 FastAPI 工程骨架、配置、health/capabilities 与 Alembic 基础；尚无业务表、任务或 AI/OCR 实现。

本机 Python：`/opt/anaconda3/bin/python3.11`（3.11.7），依赖由 uv.lock 锁定。uv 0.13.8 本次装在临时目录 `/private/tmp/zb-uv/bin/uv`；普通终端需要先安装 uv 并加入 PATH，也可将下述 uv 替换为该绝对路径。

从项目根进入 backend：

```sh
cd backend
uv sync --frozen --python /opt/anaconda3/bin/python3.11
uv run --frozen pytest -q
uv run --frozen alembic upgrade head
uv run --frozen alembic current
uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

本机 8000 已占用，本次实际验收使用 `--port 8001`。接口 `/api/v1/health`、`/api/v1/capabilities`；OpenAPI `/openapi.json`，交互文档 `/docs`。仅实现的两个路径出现在运行时契约中，完整设计仍在 docs/current/contracts。

配置自动加载根 `.env`（可复制 `.env.example`），环境变量优先。相对存储与 SQLite 路径以项目根解析，密钥用 SecretStr，响应不返回配置或密钥。CORS 逗号分隔。

capabilities 的 storage 为临时文件写读探测，database 为连接与 SELECT 1 探测，不代表业务持久层已完成。解析、OCR、转换和 workflow_api 当前均 unavailable，即使填入密钥也不会伪称适配已完成；mock 仅标记所选配置，未实现模拟工作流。

Alembic 当前无 revision、无业务表；upgrade head 仅验证基础可运行，S02 才实现模型和迁移。worker 尚未实现，无启动命令。运行数据在根 var/，不进入版本库。
