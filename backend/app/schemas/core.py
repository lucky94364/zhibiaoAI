from typing import Literal
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Context(StrictModel):
    bidder_name: str = Field(min_length=1)
    project_leader: str = Field(min_length=1)
    deadline: AwareDatetime
    timezone: str = Field(min_length=1)
    consortium_members: list[str] = Field(default_factory=list)

    @field_validator('deadline')
    @classmethod
    def utc_deadline(cls, value):
        return value.astimezone(timezone.utc)

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('timezone 必须为有效的 IANA 时区')
        return value

    @property
    def deadline_date(self):
        return self.deadline.astimezone(ZoneInfo(self.timezone)).date()

class Scope(StrictModel):
    label: str = Field(min_length=1)
    source_clause_labels: list[str] = Field(default_factory=list)
    section_titles: list[str] = Field(default_factory=list)

class ProjectCreate(StrictModel):
    name: str = Field(min_length=1)
    context: Context
    scope: Scope

class ProjectPatch(StrictModel):
    expected_input_revision: int = Field(ge=1)
    name: str = Field(default=None, min_length=1)
    context: Context = None
    scope: Scope = None

    @field_validator('name', 'context', 'scope')
    @classmethod
    def no_explicit_null(cls, value):
        if value is None:
            raise ValueError('字段不能为 null；不修改请省略')
        return value

class Project(ProjectCreate):
    project_id: str
    input_revision: int = Field(ge=1)
    state: Literal['preparing', 'reviewing', 'ready_in_scope', 'abandoned', 'archived']
    current_verification_job_id: str | None
    created_at: AwareDatetime
    updated_at: AwareDatetime

class ProjectList(StrictModel):
    items: list[Project]
    total: int

JobKind = Literal['parse', 'extract_requirements', 'extract_materials', 'verify', 'supplement', 'export']
JobState = Literal['queued', 'running', 'succeeded', 'failed', 'interrupted', 'cancelled']

class JobAccepted(StrictModel):
    job_id: str
    state: JobState
    snapshot_id: str | None

class Job(JobAccepted):
    project_id: str
    kind: JobKind
    progress: dict
    output: dict | None
    error: dict | None
    attempt: int = Field(ge=1)
    parent_job_id: str | None

class Snapshot(StrictModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str
    project_id: str
    input_revision: int = Field(ge=1)
    context: Context
    requirement_versions: list[dict]
    active_file_ids: list[str]
    active_material_ids: list[str]
    coverage: dict
    scope: Scope
    hash: str
    created_at: AwareDatetime
