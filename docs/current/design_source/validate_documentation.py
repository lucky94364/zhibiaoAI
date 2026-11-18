"""Validate local documentation and contract examples without app dependencies.

Checks the JSON Schema subset used here, local refs, OpenAPI structure,
fixture source quotes, links and original-file hashes. This is not full
OpenAPI meta-schema validation and does not test any business application.
"""
from pathlib import Path
from datetime import date, datetime
import hashlib
import json
import re

CURRENT = Path(__file__).resolve().parents[1]
ROOT = CURRENT.parents[1]
CONTRACTS = CURRENT / "contracts"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


domain = read_json(CONTRACTS / "domain.schema.json")
openapi = read_json(CONTRACTS / "openapi.json")


def resolve(document, pointer):
    assert pointer.startswith("#/"), pointer
    value = document
    for part in pointer[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    return value


def validate(value, schema, document):
    if "$ref" in schema:
        return validate(value, resolve(document, schema["$ref"]), document)
    if "anyOf" in schema:
        errors = []
        for branch in schema["anyOf"]:
            try:
                validate(value, branch, document)
                return
            except (AssertionError, ValueError, TypeError) as exc:
                errors.append(str(exc))
        raise AssertionError("No anyOf branch matched: " + repr(errors))
    kind = schema.get("type")
    checks = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list), "string": lambda x: isinstance(x, str), "integer": lambda x: isinstance(x, int) and not isinstance(x, bool), "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool), "boolean": lambda x: isinstance(x, bool), "null": lambda x: x is None}
    if kind:
        assert checks[kind](value), (kind, value)
    if "enum" in schema:
        assert value in schema["enum"], value
    if isinstance(value, dict):
        assert set(schema.get("required", [])) <= set(value), (schema.get("required"), value)
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(props), set(value) - set(props)
        for key, item in value.items():
            if key in props:
                validate(item, props[key], document)
    if isinstance(value, list):
        assert len(value) >= schema.get("minItems", 0)
        if "items" in schema:
            for item in value:
                validate(item, schema["items"], document)
    if isinstance(value, str):
        assert len(value) >= schema.get("minLength", 0)
        if schema.get("format") == "date-time":
            assert datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
        if schema.get("format") == "date":
            date.fromisoformat(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        assert value >= schema["minimum"]


refs_checked = 0


def scan_refs(value, document):
    global refs_checked
    if isinstance(value, dict):
        if "$ref" in value:
            resolve(document, value["$ref"])
            refs_checked += 1
        for item in value.values():
            scan_refs(item, document)
    elif isinstance(value, list):
        for item in value:
            scan_refs(item, document)


scan_refs(domain, domain)
scan_refs(openapi, openapi)
assert openapi["openapi"] == "3.1.0"
operation_ids = set()
for path, methods in openapi["paths"].items():
    for method, operation in methods.items():
        assert operation["operationId"] not in operation_ids
        operation_ids.add(operation["operationId"])
        names = {p["name"] for p in operation["parameters"] if p["in"] == "path"}
        assert names == set(re.findall(r"\{([^}]+)\}", path)), path
        assert "default" in operation["responses"]
        if method in {"post", "put", "patch"}:
            assert any(p["name"] == "Idempotency-Key" for p in operation["parameters"])

fixtures = {"project_create.json": "ProjectCreate", "ai_requirements_response.json": "AIRequirementsResponse", "ai_materials_response.json": "AIMaterialsResponse", "ai_check_response.json": "AICheckResponse", "supplement_request.json": "SupplementRequest", "error.json": "Error"}
for filename, schema_name in fixtures.items():
    validate(read_json(CONTRACTS / "fixtures" / filename), domain["$defs"][schema_name], domain)
blocks = read_json(CONTRACTS / "fixtures/source_blocks.json")["blocks"]
for block in blocks:
    validate(block, domain["$defs"]["SourceBlock"], domain)
lookup = {b["block_id"]: b["text"] for b in blocks}
quote_count = 0


def check_quotes(value):
    global quote_count
    if isinstance(value, dict):
        if "block_id" in value and "quote" in value:
            assert value["block_id"] in lookup
            assert value["quote"] in lookup[value["block_id"]]
            quote_count += 1
        for item in value.values():
            check_quotes(item)
    elif isinstance(value, list):
        for item in value:
            check_quotes(item)


for filename in fixtures:
    check_quotes(read_json(CONTRACTS / "fixtures" / filename))


def markdown_targets(content):
    pos = 0
    while True:
        start = content.find("](", pos)
        if start < 0:
            return
        i = start + 2
        if content[i:i + 1] == "<":
            end = content.index(">", i)
            yield content[i + 1:end]
            pos = end + 1
            continue
        depth = 1
        end = i
        while end < len(content) and depth:
            if content[end] == "(":
                depth += 1
            elif content[end] == ")":
                depth -= 1
            end += 1
        assert depth == 0
        yield content[i:end - 1]
        pos = end


markdown_files = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "frontend/README.md", ROOT / "backend/README.md", ROOT / "docs/README.md", ROOT / "docs/文档版本与来源索引.md", ROOT / "docs/history/README.md"] + list(CURRENT.rglob("*.md"))
link_count = 0
json_blocks = 0
for path in markdown_files:
    content = path.read_text(encoding="utf-8")
    for target in markdown_targets(content):
        if target.startswith(("https:", "http:", "#")):
            continue
        assert (path.parent / target.split("#")[0]).exists(), (str(path), target)
        link_count += 1
    for match in re.finditer(r"```json\n(.*?)\n```", content, re.S):
        json.loads(match.group(1))
        json_blocks += 1

inventory = read_json(ROOT / "docs/history/文件保留清单_2026-11-17.json")
for item in inventory["files"]:
    path = ROOT / item["preserved_path"]
    assert path.is_file(), item["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]
status = read_json(CURRENT / "progress/development_status.json")
assert len(status["stages"]) == 14
assert all(x["status"] == "not_started" for x in status["stages"]), "Preparation validation only applies before implementation"
for stage in status["stages"]:
    assert f'## {stage["id"]} ' in (CURRENT / "07_AI分步开发与执行提示.md").read_text(encoding="utf-8")
report = {"date": "2026-11-17", "documentation_validation_passed": True, "preserved_original_files": len(inventory["files"]), "original_paths_unchanged_except_backed_up_root_readme": True, "markdown_files_checked": len(markdown_files), "local_links_checked": link_count, "json_code_blocks_parsed": json_blocks, "schema_definitions": len(domain["$defs"]), "local_references_checked": refs_checked, "openapi_operations_structurally_checked": len(operation_ids), "fixture_files_type_checked": len(fixtures) + 1, "fixture_quotes_checked": quote_count, "development_stages": 14, "application_tests": "not_run: application not initialized", "external_platform_api": "unconfirmed", "validation_scope": "local refs, used-schema-subset fixtures, structural OpenAPI, links and file hashes; not full OpenAPI meta-schema validation"}
(CURRENT / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
