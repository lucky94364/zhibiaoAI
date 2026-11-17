# 智标 AI：投标材料核验助手

当前版本：材料核验 MVP 开发基线 V2.0，2026-11-17 已确认。参赛方向：AI＋业务流程再造。

用户输入招标文件与材料目录，系统两路提取后逐项核验，展示原文证据；补材后只重新处理变更文件和受影响要求，最终输出匹配材料与问题报告。

**开发从 [docs/current/README.md](docs/current/README.md) 开始。**采用自写前后端、解析/OCR和持久存储，集团平台承接三条 AI 工作流。工作流外部 API 尚未确认，保留直接内部模型适配。

## 当前项目状态

文档与目录约定已建立，业务应用尚未初始化；frontend/backend 目前只有说明，不能直接启动服务。下一步为 [S01 工程骨架](docs/current/07_AI分步开发与执行提示.md)。

```text
frontend/       React＋TypeScript 工作台
backend/        Python/FastAPI 业务、文件、任务和 AI 适配
docs/current/   最新开发文档、契约、阶段任务与验收
docs/history/   历史记录和整理前入口备份
docs/           原有资料保留原位
var/            后续运行数据，不纳入版本库
```

## 交给 AI 开发

使用 [分阶段开发模板](docs/current/07_AI分步开发与执行提示.md)，从 S01 逐步执行到 S14。每阶段需要实际实现、验证并记录进度；mock、真实 OCR 和真实 AI 接入分别验收。

目录规范见 [架构](docs/current/01_系统架构与目录规范.md)，配置约定见 [.env.example](.env.example)，协作规则见 [AGENTS.md](AGENTS.md)。

## 文档与样本

- [统一文档导航](docs/README.md)：原始依据、历史版本和可复用材料。
- [当前数据及 API 契约](docs/current/contracts/README.md)：后续前后端按此实现，旧契约保留作参考。
- [已有模拟材料](docs/group_platform_materials_v1/samples/manifest.json)：真实 PDF/图片输入及补材顺序。
- [旧交互原型](docs/ui_workflow_demo/README.md)：仅用于布局与交互参考，含历史范围和模拟结果。

原有文件没有删除或移动。整理前项目 README 已备份，保留校验见 [history](docs/history/README.md)。
