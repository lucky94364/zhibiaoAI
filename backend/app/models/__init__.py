"""S02 relational model. JSON evidence remains immutable in service operations."""
from sqlalchemy import (MetaData, Table, Column, String, Integer, Boolean, JSON,
                        ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index)

metadata = MetaData(naming_convention={"ix": "ix_%(table_name)s_%(column_0_name)s", "uq": "uq_%(table_name)s_%(column_0_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"})

def col(name, type_=String, nullable=False, **kw):
    return Column(name, type_, nullable=nullable, **kw)

def identity():
    return col('id', primary_key=True)

def project():
    return Column('project_id', String, ForeignKey('projects.id'), nullable=False, index=True)

def scoped(name, *columns, constraints=()):
    return Table(name, metadata, identity(), project(), *columns,
                 UniqueConstraint('project_id', 'id'), *constraints)

def ref(field, table, target='id'):
    return ForeignKeyConstraint(['project_id', field], [f'{table}.project_id', f'{table}.{target}'])

def state(field, values):
    return CheckConstraint(f"{field} IN ({','.join(repr(v) for v in values.split())})", name=f'{field}_values')

projects = Table('projects', metadata, identity(), col('name'), col('context_json', JSON), col('scope_json', JSON),
    col('input_revision', Integer), col('state'), col('current_verification_job_id', nullable=True),
    col('decision_json', JSON, nullable=True), col('created_at'), col('updated_at'),
    col('create_request_key', unique=True), col('create_request_hash'), col('create_response_json', JSON),
    col('operation_records_json', JSON),
    CheckConstraint('input_revision >= 1', name='project_revision_positive'),
    state('state', 'preparing reviewing ready_in_scope abandoned archived'))

snapshots = scoped('snapshots', col('input_revision', Integer), col('context_json', JSON),
    col('requirement_versions_json', JSON), col('active_file_ids_json', JSON), col('active_material_ids_json', JSON),
    col('coverage_json', JSON), col('scope_json', JSON), col('hash'), col('created_at'))

jobs = scoped('jobs', col('kind'), col('snapshot_id', nullable=True), col('request_key'), col('request_hash'),
    col('state'), col('progress_json', JSON), col('input_json', JSON), col('output_json', JSON, nullable=True),
    col('attempt', Integer), col('parent_job_id', nullable=True), col('heartbeat_at', nullable=True),
    col('error_json', JSON, nullable=True), col('provider_run_ids_json', JSON), col('created_at'),
    col('started_at', nullable=True), col('ended_at', nullable=True), col('claim_token', nullable=True),
    constraints=(UniqueConstraint('project_id', 'request_key'), ref('snapshot_id', 'snapshots'), ref('parent_job_id', 'jobs'),
        CheckConstraint('attempt >= 1', name='job_attempt_positive'),
        state('kind', 'parse extract_requirements extract_materials verify supplement export'),
        state('state', 'queued running succeeded failed interrupted cancelled')))
Index('ix_jobs_claim', jobs.c.state, jobs.c.created_at)
Index('ix_jobs_recovery', jobs.c.state, jobs.c.heartbeat_at)

files = scoped('files', col('logical_file_id'), col('version_no', Integer), col('replaces_file_id', nullable=True),
    col('source_kind'), col('original_name'), col('relative_path'), col('sha256'), col('storage_key'),
    col('active_state'), col('parse_state'), col('current_parse_job_id', nullable=True), col('error_json', JSON, nullable=True),
    constraints=(UniqueConstraint('logical_file_id', 'version_no'), ref('replaces_file_id', 'files'), ref('current_parse_job_id', 'jobs'),
        CheckConstraint('version_no >= 1', name='file_version_positive'),
        state('active_state', 'pending active superseded disabled'), state('parse_state', 'pending processing succeeded partial failed')))
Index('ix_files_project_state', files.c.project_id, files.c.active_state)

source_blocks = scoped('source_blocks', col('file_id'), col('parse_job_id'), col('page_index', Integer),
    col('printed_page_label', nullable=True), col('section', nullable=True), col('text'), col('bbox_json', JSON, nullable=True),
    col('method'), col('quality_json', JSON), col('page_image_key', nullable=True),
    constraints=(ref('file_id', 'files'), ref('parse_job_id', 'jobs'), CheckConstraint('page_index >= 0', name='page_index_nonnegative')))
Index('ix_source_blocks_file_parse', source_blocks.c.file_id, source_blocks.c.parse_job_id)

requirements = Table('requirements', metadata, col('requirement_id', primary_key=True), col('revision', Integer, primary_key=True),
    project(), col('title'), col('category'), col('subject_role'), col('expected_material_types_json', JSON),
    col('conditions_json', JSON), col('logic_json', JSON), col('source_refs_json', JSON), col('phase'),
    col('ambiguities_json', JSON), col('content_hash'), UniqueConstraint('project_id', 'requirement_id', 'revision'),
    CheckConstraint('revision >= 1', name='requirement_revision_positive'))

materials = scoped('materials', col('file_ids_json', JSON), col('extraction_job_id'), col('supersedes_material_id', nullable=True),
    col('material_type'), col('entity_name', nullable=True), col('person_name', nullable=True), col('product_model', nullable=True),
    col('facts_json', JSON), col('extraction_state'), col('artifact_state'), col('content_hash'),
    constraints=(ref('extraction_job_id', 'jobs'), ref('supersedes_material_id', 'materials')))
Index('ix_materials_current', materials.c.project_id, materials.c.artifact_state)

check_results = scoped('check_results', col('job_id'), col('snapshot_id'), col('requirement_id'), col('requirement_revision', Integer),
    col('check_state'), col('condition_results_json', JSON), col('candidate_ids_json', JSON), col('evidence_refs_json', JSON),
    col('issues_json', JSON), col('supplement_json', JSON), col('dependency_hash'), col('provider'), col('is_simulated', Boolean),
    constraints=(ref('job_id', 'jobs'), ref('snapshot_id', 'snapshots'),
        ForeignKeyConstraint(['project_id', 'requirement_id', 'requirement_revision'], ['requirements.project_id', 'requirements.requirement_id', 'requirements.revision']),
        state('check_state', 'supported partial missing contradicted needs_review')))
Index('ix_check_results_job', check_results.c.job_id)

review_records = scoped('review_records', col('target_kind'), col('target_id'), col('target_revision', Integer, nullable=True),
    col('target_content_hash'), col('decision'), col('note'), col('actor_id'), col('snapshot_id', nullable=True), col('created_at'),
    constraints=(ref('snapshot_id', 'snapshots'), state('target_kind', 'requirement check')))
Index('ix_review_records_target', review_records.c.project_id, review_records.c.target_kind, review_records.c.target_id)

supplement_operations = scoped('supplement_operations', col('operation'), col('target_file_id', nullable=True),
    col('new_file_ids_json', JSON), col('state'), col('job_id', nullable=True), col('base_input_revision', Integer),
    col('affected_requirement_ids_json', JSON), col('request_key'), col('error_json', JSON, nullable=True),
    constraints=(UniqueConstraint('project_id', 'request_key'), ref('target_file_id', 'files'), ref('job_id', 'jobs'),
        state('operation', 'add replace'), state('state', 'pending processing committed rechecking completed failed recheck_failed'),
        CheckConstraint("operation != 'replace' OR target_file_id IS NOT NULL", name='replace_requires_target')))

exports = scoped('exports', col('snapshot_id'), col('verification_job_id'), col('kind'), col('state'),
    col('artifact_keys_json', JSON), col('result_bindings_json', JSON), col('is_simulated', Boolean), col('created_at'),
    col('error_json', JSON, nullable=True), constraints=(ref('snapshot_id', 'snapshots'), ref('verification_job_id', 'jobs')))
