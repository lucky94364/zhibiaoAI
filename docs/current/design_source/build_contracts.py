"""Build platform-independent DESIGN contracts, not application code."""
from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contracts"
OUT.mkdir(exist_ok=True)
S = {}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def array(item):
    return {"type": "array", "items": item}


def obj(properties, required=None, extra=False):
    return {"type": "object", "properties": properties, "required": list(properties) if required is None else required, "additionalProperties": extra}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


text = {"type": "string"}
nonempty = {"type": "string", "minLength": 1}
integer = {"type": "integer", "minimum": 0}
revision = {"type": "integer", "minimum": 1}
boolean = {"type": "boolean"}
json_object = {"type": "object"}
strings = array(text)
S["Id"] = nonempty
S["Timestamp"] = {"type": "string", "format": "date-time"}
S["Context"] = obj({"bidder_name": nonempty, "project_leader": nonempty, "deadline": ref("Timestamp"), "timezone": nonempty, "consortium_members": strings}, ["bidder_name", "project_leader", "deadline", "timezone"])
S["AIContext"] = deepcopy(S["Context"])
S["AIContext"]["properties"]["deadline_date"] = {"type": "string", "format": "date"}
S["AIContext"]["required"].append("deadline_date")
S["Scope"] = obj({"label": nonempty, "source_clause_labels": strings, "section_titles": strings}, ["label"])
S["SourceRef"] = obj({"block_id": ref("Id"), "quote": nonempty})
S["SourceBlock"] = obj({"block_id": ref("Id"), "file_id": ref("Id"), "parse_job_id": ref("Id"), "page_index": nullable(revision), "printed_page_label": nullable(text), "section": nullable(text), "text": text, "method": enum("native_text", "ocr", "manual_correction"), "bbox": nullable(json_object), "quality": json_object}, ["block_id", "file_id", "parse_job_id", "page_index", "text", "method", "bbox", "quality"])
S["ProjectCreate"] = obj({"name": nonempty, "context": ref("Context"), "scope": ref("Scope")})
S["Project"] = obj({"project_id": ref("Id"), "name": nonempty, "context": ref("Context"), "scope": ref("Scope"), "input_revision": revision, "state": enum("preparing", "reviewing", "ready_in_scope", "abandoned", "archived"), "current_verification_job_id": nullable(ref("Id")), "created_at": ref("Timestamp"), "updated_at": ref("Timestamp")})
S["ProjectPatch"] = obj({"expected_input_revision": revision, "name": nonempty, "context": ref("Context"), "scope": ref("Scope")}, ["expected_input_revision"])
status = enum("available", "unavailable", "not_configured", "unknown")
S["Capabilities"] = obj({"ai_provider": enum("mock", "haier_workflow", "internal_model"), "is_simulated": boolean, "parser_pdf": status, "ocr": status, "word_converter": status, "storage": status, "database": status, "workflow_api": status})
S["FileRecord"] = obj({"file_id": ref("Id"), "project_id": ref("Id"), "logical_file_id": ref("Id"), "version_no": revision, "replaces_file_id": nullable(ref("Id")), "source_kind": enum("tender", "material"), "original_name": nonempty, "relative_path": text, "sha256": text, "active_state": enum("pending", "active", "superseded", "disabled"), "parse_state": enum("pending", "processing", "succeeded", "partial", "failed"), "page_count": nullable(integer), "error": nullable(json_object)})
S["FileDetail"] = obj({"file": ref("FileRecord"), "blocks": array(ref("SourceBlock")), "issues": strings})
S["Fact"] = obj({"fact_id": ref("Id"), "field_key": nonempty, "raw_value": {}, "normalized_value": {}, "unit": nullable(text), "extraction_state": enum("clear", "absent", "unclear", "conflicting"), "source_refs": array(ref("SourceRef"))})
S["FactCandidate"] = deepcopy(S["Fact"])
del S["FactCandidate"]["properties"]["fact_id"]
S["FactCandidate"]["required"].remove("fact_id")
S["Condition"] = obj({"condition_key": nonempty, "description": nonempty, "field_key": nonempty, "operator": enum("eq", "gte", "lte", "in", "eq_context", "gte_context_date", "lte_context_date", "semantic", "unknown"), "expected": {}, "unit": nullable(text), "source_refs": array(ref("SourceRef"))})
S["Logic"] = {"anyOf": [nonempty, obj({"all": {"type": "array", "minItems": 1, "items": ref("Logic")}}), obj({"any": {"type": "array", "minItems": 1, "items": ref("Logic")}})]}
S["RequirementCandidate"] = obj({"title": nonempty, "category": enum("eligibility", "disqualification", "scoring", "submission", "delivery", "unknown"), "subject_role": nonempty, "expected_material_types": strings, "conditions": array(ref("Condition")), "logic": ref("Logic"), "phase": enum("bid", "delivery", "unknown"), "source_refs": array(ref("SourceRef")), "ambiguities": strings})
S["Requirement"] = deepcopy(S["RequirementCandidate"])
S["Requirement"]["properties"].update({"requirement_id": ref("Id"), "revision": revision, "review_state": enum("pending", "confirmed", "stale"), "content_hash": text})
S["Requirement"]["required"] += ["requirement_id", "revision", "review_state", "content_hash"]
S["RequirementUpdate"] = obj({"expected_revision": revision, "candidate": ref("RequirementCandidate")})
material_type = enum("business_license", "qualification_certificate", "personnel_certificate", "financial_report", "performance_contract", "product_document", "unknown")
S["MaterialCandidate"] = obj({"material_type": material_type, "title": nonempty, "entity_name": nullable(text), "person_name": nullable(text), "product_model": nullable(text), "source_block_ids": strings, "facts": array(ref("FactCandidate")), "questions": strings})
S["Material"] = deepcopy(S["MaterialCandidate"])
S["Material"]["properties"]["facts"] = array(ref("Fact"))
S["Material"]["properties"].update({"material_id": ref("Id"), "file_ids": array(ref("Id")), "extraction_job_id": ref("Id"), "artifact_state": enum("current", "superseded"), "extraction_state": enum("usable", "partial", "needs_review", "failed"), "content_hash": text})
S["Material"]["properties"]["supersedes_material_id"] = nullable(ref("Id"))
S["Material"]["required"] += ["material_id", "file_ids", "extraction_job_id", "artifact_state", "extraction_state", "content_hash"]
S["EvidenceRef"] = obj({"material_id": ref("Id"), "fact_id": ref("Id"), "block_id": ref("Id"), "quote": nonempty})
S["ConditionResult"] = obj({"condition_key": nonempty, "state": enum("pass", "fail", "unknown", "not_applicable"), "reason": nonempty, "evidence_refs": array(ref("EvidenceRef"))})
S["SupplementAdvice"] = obj({"material_type": text, "subject": text, "required_content": text, "suggested_role": text})
check_state = enum("supported", "partial", "missing", "contradicted", "needs_review")
S["AICheckResponse"] = obj({"requirement_id": ref("Id"), "check_state": check_state, "condition_results": array(ref("ConditionResult")), "conflicts": strings, "issues": strings, "supplement_requests": array(ref("SupplementAdvice"))})
S["CheckResult"] = deepcopy(S["AICheckResponse"])
S["CheckResult"]["properties"].update({"check_id": ref("Id"), "job_id": ref("Id"), "snapshot_id": ref("Id"), "requirement_revision": revision, "candidate_material_ids": array(ref("Id")), "dependency_hash": text, "provider": enum("mock", "haier_workflow", "internal_model"), "is_simulated": boolean, "created_at": ref("Timestamp")})
S["CheckResult"]["required"] += ["check_id", "job_id", "snapshot_id", "requirement_revision", "candidate_material_ids", "dependency_hash", "provider", "is_simulated", "created_at"]
S["CheckView"] = obj({"requirement_id": ref("Id"), "requirement_revision": revision, "result": nullable(ref("CheckResult")), "binding_kind": enum("computed", "reused", "pending"), "validity": enum("current", "stale", "historical", "pending"), "review_state": enum("pending", "confirmed", "stale"), "review_record_id": nullable(ref("Id")), "reuse_reason": nullable(text)})
S["CheckMatrix"] = obj({"project_id": ref("Id"), "input_revision": revision, "verification_job_id": nullable(ref("Id")), "snapshot_id": nullable(ref("Id")), "items": array(ref("CheckView")), "coverage": json_object, "has_stale": boolean, "is_simulated": boolean})
job_state = enum("queued", "running", "succeeded", "failed", "interrupted", "cancelled")
S["JobAccepted"] = obj({"job_id": ref("Id"), "state": job_state, "snapshot_id": nullable(ref("Id"))})
S["Job"] = obj({"job_id": ref("Id"), "project_id": ref("Id"), "kind": enum("parse", "extract_requirements", "extract_materials", "verify", "supplement", "export"), "state": job_state, "snapshot_id": nullable(ref("Id")), "progress": json_object, "output": nullable(json_object), "error": nullable(json_object), "attempt": revision, "parent_job_id": nullable(ref("Id"))})
S["ParseRequest"] = obj({"force": boolean}, [])
S["ExtractionRequest"] = obj({"file_ids": {"type": "array", "items": ref("Id"), "minItems": 1}, "expected_input_revision": revision, "scope": ref("Scope")}, ["file_ids", "expected_input_revision"])
S["VerifyRequest"] = obj({"requirement_ids": {"type": "array", "items": ref("Id"), "minItems": 1}, "recheck_requirement_ids": array(ref("Id")), "expected_input_revision": revision}, ["requirement_ids", "expected_input_revision"])
S["MaterialCorrectionRequest"] = obj({"expected_input_revision": revision, "reason": nonempty, "corrections": {"type": "array", "minItems": 1, "items": obj({"fact_id": ref("Id"), "source_block_id": ref("Id"), "transcription_text": nonempty, "normalized_value": {}, "unit": nullable(text)})}})
S["ReviewRequest"] = obj({"target_kind": enum("requirement", "check"), "target_id": ref("Id"), "target_revision": nullable(revision), "expected_input_revision": revision, "decision": enum("confirm", "request_changes"), "note": text})
S["ReviewRecord"] = obj({"review_id": ref("Id"), "target_kind": enum("requirement", "check"), "target_id": ref("Id"), "target_revision": nullable(revision), "decision": enum("confirm", "request_changes"), "note": text, "actor_id": nonempty, "created_at": ref("Timestamp")})
S["SupplementRequest"] = obj({"operation": enum("add", "replace"), "new_file_ids": {"type": "array", "items": ref("Id"), "minItems": 1}, "target_file_id": nullable(ref("Id")), "expected_input_revision": revision, "reason": text}, ["operation", "new_file_ids", "expected_input_revision", "reason"])
S["SupplementOperation"] = obj({"operation_id": ref("Id"), "operation": enum("add", "replace"), "state": enum("pending", "processing", "committed", "rechecking", "completed", "failed", "recheck_failed"), "job_id": ref("Id"), "target_file_id": nullable(ref("Id")), "new_file_ids": array(ref("Id")), "affected_requirement_ids": array(ref("Id")), "error": nullable(json_object)})
S["ExportRequest"] = obj({"kind": enum("report", "reviewed_bundle"), "expected_input_revision": revision, "requirement_ids": {"type": "array", "items": ref("Id"), "minItems": 1}})
S["ExportRecord"] = obj({"export_id": ref("Id"), "job_id": ref("Id"), "snapshot_id": nullable(ref("Id")), "kind": enum("report", "reviewed_bundle"), "state": enum("queued", "running", "succeeded", "failed"), "is_simulated": boolean, "download_url": nullable(text), "error": nullable(json_object)})
S["DecisionRequest"] = obj({"decision": enum("abandoned", "archived"), "reason": nonempty, "expected_input_revision": revision})
S["Error"] = obj({"error": obj({"code": nonempty, "message": nonempty, "retryable": boolean, "details": json_object}), "request_id": nonempty})
S["AIRequirementsResponse"] = obj({"candidates": array(ref("RequirementCandidate")), "questions": strings, "processed_block_ids": strings, "unresolved_block_ids": strings})
S["AIMaterialsResponse"] = obj({"material_candidates": array(ref("MaterialCandidate")), "questions": strings, "unclassified_block_ids": strings})
S["Health"] = obj({"status": enum("ok"), "version": nonempty, "timestamp": ref("Timestamp")})
for name in ["Project", "FileRecord", "Requirement", "Material"]:
    S[name + "List"] = obj({"items": array(ref(name)), "total": integer})

domain = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://zhb.example.invalid/design/v2/domain.schema.json", "title": "智标AI材料核验设计数据类型 V2", "$defs": S}
(OUT / "domain.schema.json").write_text(json.dumps(domain, ensure_ascii=False, indent=2), encoding="utf-8")


def openapi_refs(value):
    if isinstance(value, dict):
        return {k: (v.replace("#/$defs/", "#/components/schemas/") if k == "$ref" else openapi_refs(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [openapi_refs(v) for v in value]
    return value


def oref(name):
    return {"$ref": "#/components/schemas/" + name}


paths = {}


def endpoint(path, method, operation, output, status_code=200, request=None, binary=None, query=None, multipart=False):
    parameters = []
    import re
    for key in re.findall(r"\{([^}]+)\}", path):
        parameters.append({"name": key, "in": "path", "required": True, "schema": revision if key == "page_index" else nonempty})
    if method in {"post", "put", "patch"}:
        parameters += [{"name": "Idempotency-Key", "in": "header", "required": True, "schema": nonempty}, {"name": "X-Actor-Id", "in": "header", "required": False, "schema": {"type": "string", "default": "demo-user"}, "description": "本机试验操作标签，不是认证"}]
    for name, schema in query or []:
        parameters.append({"name": name, "in": "query", "required": False, "schema": schema})
    content = {binary: {"schema": {"type": "string", "format": "binary"}}} if binary else {"application/json": {"schema": oref(output)}}
    entry = {"operationId": operation, "summary": operation, "parameters": parameters, "responses": {str(status_code): {"description": "设计成功响应；技术成功不等于条件满足", "content": content}, "default": {"description": "类型化错误", "content": {"application/json": {"schema": oref("Error")}}}}}
    if multipart:
        entry["requestBody"] = {"required": True, "content": {"multipart/form-data": {"schema": obj({"file": {"type": "string", "format": "binary"}, "source_kind": enum("tender", "material"), "relative_path": text}, ["file", "source_kind"])}}}
    elif request:
        entry["requestBody"] = {"required": True, "content": {"application/json": {"schema": oref(request)}}}
    paths.setdefault(path, {})[method] = entry


endpoint("/health", "get", "get_health", "Health")
endpoint("/capabilities", "get", "get_capabilities", "Capabilities")
endpoint("/projects", "get", "list_projects", "ProjectList")
endpoint("/projects", "post", "create_project", "Project", 201, "ProjectCreate")
endpoint("/projects/{project_id}", "get", "get_project", "Project")
endpoint("/projects/{project_id}", "patch", "update_project", "Project", request="ProjectPatch")
endpoint("/projects/{project_id}/files", "get", "list_files", "FileRecordList")
endpoint("/projects/{project_id}/files", "post", "upload_file", "FileRecord", 201, multipart=True)
endpoint("/files/{file_id}", "get", "get_file", "FileDetail")
endpoint("/files/{file_id}/content", "get", "download_file", None, binary="application/octet-stream")
endpoint("/files/{file_id}/pages/{page_index}", "get", "get_page_image", None, binary="image/png")
endpoint("/files/{file_id}/parse", "post", "parse_file", "JobAccepted", 202, "ParseRequest")
endpoint("/jobs/{job_id}", "get", "get_job", "Job")
endpoint("/jobs/{job_id}/retry", "post", "retry_job", "JobAccepted", 202)
endpoint("/projects/{project_id}/requirement-extractions", "post", "extract_requirements", "JobAccepted", 202, "ExtractionRequest")
endpoint("/projects/{project_id}/requirements", "get", "list_requirements", "RequirementList")
endpoint("/requirements/{requirement_id}", "put", "revise_requirement", "Requirement", request="RequirementUpdate")
endpoint("/projects/{project_id}/material-extractions", "post", "extract_materials", "JobAccepted", 202, "ExtractionRequest")
endpoint("/projects/{project_id}/materials", "get", "list_materials", "MaterialList", query=[("include_history", boolean)])
endpoint("/materials/{material_id}/corrections", "post", "correct_material_fields", "Material", request="MaterialCorrectionRequest")
endpoint("/projects/{project_id}/verifications", "post", "start_verification", "JobAccepted", 202, "VerifyRequest")
endpoint("/projects/{project_id}/checks", "get", "get_check_matrix", "CheckMatrix")
endpoint("/projects/{project_id}/reviews", "post", "review_target", "ReviewRecord", request="ReviewRequest")
endpoint("/projects/{project_id}/supplements", "post", "start_supplement", "SupplementOperation", 202, "SupplementRequest")
endpoint("/supplements/{operation_id}", "get", "get_supplement", "SupplementOperation")
endpoint("/projects/{project_id}/exports", "post", "create_export", "ExportRecord", 202, "ExportRequest")
endpoint("/exports/{export_id}", "get", "get_export", "ExportRecord")
endpoint("/exports/{export_id}/content", "get", "download_export", None, binary="application/zip")
endpoint("/projects/{project_id}/decision", "post", "record_decision", "Project", request="DecisionRequest")
openapi = {"openapi": "3.1.0", "info": {"title": "智标AI材料核验设计 API", "version": "2.0.0", "description": "设计契约，当前尚未实现业务服务；集团平台协议尚未确认。X-Actor-Id仅为本机试验标签。"}, "servers": [{"url": "http://localhost:8000/api/v1", "description": "S01以后约定的开发地址，当前无服务"}], "paths": paths, "components": {"schemas": openapi_refs(S)}}
(OUT / "openapi.json").write_text(json.dumps(openapi, ensure_ascii=False, indent=2), encoding="utf-8")

# Small, explicitly synthetic in-memory contract fixtures, not OCR outputs.
blocks = [{"block_id": "BLK-T-Q02", "file_id": "DOC-T-EXAMPLE", "parse_job_id": "JOB-PARSE-T", "page_index": 1, "text": "提供拟派负责人持有的项目服务能力证书（模拟），持有人须为林明，所属单位须为投标主体，有效期须覆盖投标截止日期。", "method": "native_text", "bbox": None, "quality": {}}, {"block_id": "BLK-M-PERSON", "file_id": "DOC-M-EXAMPLE", "parse_job_id": "JOB-PARSE-M", "page_index": 1, "text": "项目服务能力证书（模拟）\n持有人：林明。\n所属单位：青禾数智测试有限公司。\n有效期自：2024年1月1日。\n有效期至：2026年10月31日。", "method": "ocr", "bbox": None, "quality": {"fixture_only": True}}]
candidate = {"title": "负责人证书有效性", "category": "eligibility", "subject_role": "leader", "expected_material_types": ["personnel_certificate"], "conditions": [{"condition_key": "C01", "description": "结束日覆盖投标截止日（本契约示例仅含这一条件）", "field_key": "valid_until", "operator": "gte_context_date", "expected": "deadline_date", "unit": None, "source_refs": [{"block_id": "BLK-T-Q02", "quote": "有效期须覆盖投标截止日期"}]}], "logic": {"all": ["C01"]}, "phase": "bid", "source_refs": [{"block_id": "BLK-T-Q02", "quote": "有效期须覆盖投标截止日期"}], "ambiguities": []}
fact = {"field_key": "valid_until", "raw_value": "2026年10月31日", "normalized_value": "2026-10-31", "unit": None, "extraction_state": "clear", "source_refs": [{"block_id": "BLK-M-PERSON", "quote": "有效期至：2026年10月31日"}]}
material = {"material_type": "personnel_certificate", "title": "负责人证书", "entity_name": "青禾数智测试有限公司", "person_name": "林明", "product_model": None, "source_block_ids": ["BLK-M-PERSON"], "facts": [fact], "questions": []}
fixtures = {
    "project_create.json": {"name": "材料核验模拟项目", "context": {"bidder_name": "青禾数智测试有限公司", "project_leader": "林明", "deadline": "2026-11-30T09:00:00+08:00", "timezone": "Asia/Shanghai"}, "scope": {"label": "模拟Q01-Q04", "source_clause_labels": ["Q01", "Q02", "Q03", "Q04"]}},
    "source_blocks.json": {"note": "合成的内存契约输入，只用于类型与引用校验；不代表真实PDF/OCR输出，不能用于证明OCR效果", "blocks": blocks},
    "ai_requirements_response.json": {"candidates": [candidate], "questions": [], "processed_block_ids": ["BLK-T-Q02"], "unresolved_block_ids": []},
    "ai_materials_response.json": {"material_candidates": [material], "questions": [], "unclassified_block_ids": []},
    "ai_check_response.json": {"requirement_id": "REQ-EXAMPLE", "check_state": "contradicted", "condition_results": [{"condition_key": "C01", "state": "fail", "reason": "结束日早于模拟截止日", "evidence_refs": [{"material_id": "MAT-EXAMPLE", "fact_id": "FCT-EXAMPLE", "block_id": "BLK-M-PERSON", "quote": "有效期至：2026年10月31日"}]}], "conflicts": [], "issues": ["证书过期"], "supplement_requests": [{"material_type": "personnel_certificate", "subject": "林明", "required_content": "覆盖要求截止日的有效证书", "suggested_role": "人员资料提供方"}]},
    "supplement_request.json": {"operation": "replace", "new_file_ids": ["DOC-new"], "target_file_id": "DOC-old", "expected_input_revision": 3, "reason": "补充有效证书"},
    "error.json": {"error": {"code": "VERSION_CONFLICT", "message": "输入版本已变化", "retryable": False, "details": {"expected": 3, "current": 4}}, "request_id": "REQ-request-example"}
}
fixtures_dir = OUT / "fixtures"
fixtures_dir.mkdir(exist_ok=True)
for name, value in fixtures.items():
    (fixtures_dir / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"schemas": len(S), "paths": len(paths), "operations": sum(len(v) for v in paths.values()), "fixtures": len(fixtures)}, ensure_ascii=False))
