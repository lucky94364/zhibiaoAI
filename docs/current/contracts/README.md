# 当前设计契约

- `domain.schema.json`：JSON Schema 2020-12，API 与 AI 数据类型。
- `openapi.json`：OpenAPI 3.1 设计，业务地址 /api/v1；不是集团平台接口，也不是已运行服务。
- `fixtures/`：小型合成内存契约示例，只用于类型、字段和引用校验。负责人示例仅展示有效期单条件，不代表完整 Q02 要求。

真实文件处理测试使用 [既有模拟样本](../../group_platform_materials_v1/samples/manifest.json)。不能用内存 fixture 代替实际 PDF、OCR 或真实模型验收。

生成脚本：`../design_source/build_contracts.py`，不依赖应用；类型/引用及链接检查脚本另见同目录 validate_documentation.py。

本契约约束结构和枚举；来源归属、当前版本、逻辑键完整性、replace 必须目标等跨字段约束还要按数据与状态文档实现服务端校验。
