# API 与接口契约

机器可读文件：`contracts/openapi.json`；数据结构：`contracts/domain.schema.json`。都是本项目设计，非集团平台 API。

## 1. 公共约定

- 基址 `/api/v1`。JSON 字段使用 snake_case；ID 为字符串；时间有偏移。
- 列表返回 items/total；首版先返回试点规模全部结果，不预造复杂分页。
- 长任务 202 返回 job_id、state、snapshot_id；前端轮询 GET /jobs/{id}。
- 创建资源 201，读取/确认 200；409 版本冲突，422 输入错误，503 依赖不可用。
- 修改请求使用 Idempotency-Key。相同键同体返回原操作；同键异体 409。
- 本机试验的 X-Actor-Id 是操作标签，用于记录，不是生产认证；真实身份集成后替换来源。
- 前端不提交数据库行或存储路径任意更新，只调用固定业务操作。

## 2. 路由总表

| 方法与路径（省略基址） | 行为 | 阶段 |
|---|---|---|
| GET /health | 应用存活 | S01 |
| GET /capabilities | AI、OCR、转换、存储是否配置及真实可用 | S01/S04/S05 |
| GET/POST /projects | 项目列表/创建 | S02 |
| GET/PATCH /projects/{project_id} | 读取/更新上下文；更新触发失效 | S02/S09 |
| POST /projects/{project_id}/files | 单文件 multipart，附 source_kind、relative_path | S03 |
| GET /projects/{project_id}/files | 文件、目录及状态列表 | S03 |
| GET /files/{file_id} | 文件详情及页面/来源信息 | S03/S04 |
| GET /files/{file_id}/content | 下载授权范围内原件 | S03 |
| GET /files/{file_id}/pages/{page_index} | 页面图；未就绪返回明确错误 | S04 |
| POST /files/{file_id}/parse | 创建解析任务 | S04 |
| GET /jobs/{job_id} | 进度、输出、失败及历史状态 | S02 |
| POST /jobs/{job_id}/retry | 创建带 parent_job_id 的重试，不重复副作用 | S04/S09 |
| POST /projects/{project_id}/requirement-extractions | 选定文件/范围提取要求 | S06 |
| GET /projects/{project_id}/requirements | 当前要求及确认情况 | S06 |
| PUT /requirements/{requirement_id} | expected_revision 修订，创建新版本 | S06 |
| POST /projects/{project_id}/material-extractions | 当前解析产物分类与字段提取 | S07 |
| GET /projects/{project_id}/materials | 当前材料；可选 include_history | S07 |
| POST /materials/{material_id}/corrections | 人工核对原页后修订字段，发布新材料产物 | S07/S09 |
| POST /projects/{project_id}/verifications | 对选定要求创建核验运行 | S08/S09 |
| GET /projects/{project_id}/checks | 服务端组装的当前结果矩阵 | S08/S09 |
| POST /projects/{project_id}/reviews | 确认确切要求版本或当前核验结果 | S06/S08 |
| POST /projects/{project_id}/supplements | 上传新文件引用＋add/replace，完整补材操作 | S09 |
| GET /supplements/{operation_id} | 补材提交和重检状态 | S09 |
| POST /projects/{project_id}/exports | report 或 reviewed_bundle | S11 |
| GET /exports/{export_id} | 导出状态、范围和下载信息 | S11 |
| GET /exports/{export_id}/content | 下载导出文件 | S11 |
| POST /projects/{project_id}/decision | 用户明确放弃/归档，保留原因 | S11 |

上传与补材分开：先上传 pending 新文件，supplements 传这些 file_id 及替换目标。普通首轮文件由解析/提取成功后进入当前集合；pending 上传不直接污染核验快照。

VerifyRequest.requirement_ids 定义整次报告范围；可选 recheck_requirement_ids 是其中需要重新计算的子集，不填时全算。服务端必须扩大遗漏的受影响项。补材内部继承最近核验范围；用户新增范围时明确重新选择，报告不扩大宣称。

字段修订使用 MaterialCorrectionRequest，fact_id 和 source_block_id 必须属于当前材料。用户对照原页填写 transcription_text、规范值及理由；后端创建 method=manual_correction 的新来源块和新材料产物，记录操作人，旧 OCR 与字段不改。返回新材料，相关结果失效并进入重检；人工誊写的来源在界面显式标记。

## 3. 示例请求

```json
{
  "name": "材料核验模拟项目",
  "context": {
    "bidder_name": "青禾数智测试有限公司",
    "project_leader": "林明",
    "deadline": "2026-11-30T09:00:00+08:00",
    "timezone": "Asia/Shanghai"
  },
  "scope": {"label": "模拟Q01-Q04", "source_clause_labels": ["Q01", "Q02", "Q03", "Q04"]}
}
```

新增/替换提交：

```json
{
  "operation": "replace",
  "new_file_ids": ["DOC-new"],
  "target_file_id": "DOC-old",
  "expected_input_revision": 3,
  "reason": "补充有效期覆盖截止日的证书"
}
```

接口不接受客户端直接声称 check_state=supported。模型结果必须经后端校验，人工意见通过 review 追加。

## 4. 错误结构

```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "材料版本已变化，请刷新后重试",
    "retryable": false,
    "details": {"expected": 3, "current": 4}
  },
  "request_id": "request-example"
}
```

错误码至少包含：VERSION_CONFLICT、IDEMPOTENCY_CONFLICT、FILE_UNSUPPORTED、FILE_PARSE_FAILED、OCR_UNAVAILABLE、CONVERTER_UNAVAILABLE、SOURCE_REFERENCE_INVALID、REQUIREMENT_UNCONFIRMED、INPUT_NOT_READY、AI_NOT_CONFIGURED、AI_OUTPUT_INVALID、EXPORT_NOT_READY、RESOURCE_NOT_FOUND。

401/403 留给实际身份系统接入；不能用未知外部 API 的错误格式替代本系统错误。

## 5. 契约维护

S01 起按契约编写 Pydantic 类型并由应用生成 OpenAPI；把路径、字段和枚举与设计对照。实现差异先修正代码，确有必要改变契约时同步文档、前端类型及测试。

本目录 OpenAPI 不包含集团平台 URL、模型协议或密钥。实际工作流接口必须由已验证示例实现适配。
