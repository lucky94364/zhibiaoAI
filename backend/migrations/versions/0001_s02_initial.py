"""S02: initial eleven business tables."""
from alembic import op
import sqlalchemy as sa

revision = '0001_s02'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Frozen S02 schema; later changes require a new revision.
    op.create_table('projects',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('context_json', sa.JSON(), nullable=False),
    sa.Column('scope_json', sa.JSON(), nullable=False),
    sa.Column('input_revision', sa.Integer(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('current_verification_job_id', sa.String(), nullable=True),
    sa.Column('decision_json', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.Column('updated_at', sa.String(), nullable=False),
    sa.Column('create_request_key', sa.String(), nullable=False),
    sa.Column('create_request_hash', sa.String(), nullable=False),
    sa.Column('create_response_json', sa.JSON(), nullable=False),
    sa.Column('operation_records_json', sa.JSON(), nullable=False),
    sa.CheckConstraint("state IN ('preparing','reviewing','ready_in_scope','abandoned','archived')", name='state_values'),
    sa.CheckConstraint('input_revision >= 1', name='project_revision_positive'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_projects')),
    sa.UniqueConstraint('create_request_key', name=op.f('uq_projects_create_request_key'))
    )
    op.create_table('requirements',
    sa.Column('requirement_id', sa.String(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('subject_role', sa.String(), nullable=False),
    sa.Column('expected_material_types_json', sa.JSON(), nullable=False),
    sa.Column('conditions_json', sa.JSON(), nullable=False),
    sa.Column('logic_json', sa.JSON(), nullable=False),
    sa.Column('source_refs_json', sa.JSON(), nullable=False),
    sa.Column('phase', sa.String(), nullable=False),
    sa.Column('ambiguities_json', sa.JSON(), nullable=False),
    sa.Column('content_hash', sa.String(), nullable=False),
    sa.CheckConstraint('revision >= 1', name='requirement_revision_positive'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_requirements_project_id_projects')),
    sa.PrimaryKeyConstraint('requirement_id', 'revision', name=op.f('pk_requirements')),
    sa.UniqueConstraint('project_id', 'requirement_id', 'revision', name=op.f('uq_requirements_project_id'))
    )
    op.create_index(op.f('ix_requirements_project_id'), 'requirements', ['project_id'], unique=False)
    op.create_table('snapshots',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('input_revision', sa.Integer(), nullable=False),
    sa.Column('context_json', sa.JSON(), nullable=False),
    sa.Column('requirement_versions_json', sa.JSON(), nullable=False),
    sa.Column('active_file_ids_json', sa.JSON(), nullable=False),
    sa.Column('active_material_ids_json', sa.JSON(), nullable=False),
    sa.Column('coverage_json', sa.JSON(), nullable=False),
    sa.Column('scope_json', sa.JSON(), nullable=False),
    sa.Column('hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_snapshots_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_snapshots')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_snapshots_project_id'))
    )
    op.create_index(op.f('ix_snapshots_project_id'), 'snapshots', ['project_id'], unique=False)
    op.create_table('jobs',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('snapshot_id', sa.String(), nullable=True),
    sa.Column('request_key', sa.String(), nullable=False),
    sa.Column('request_hash', sa.String(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('progress_json', sa.JSON(), nullable=False),
    sa.Column('input_json', sa.JSON(), nullable=False),
    sa.Column('output_json', sa.JSON(), nullable=True),
    sa.Column('attempt', sa.Integer(), nullable=False),
    sa.Column('parent_job_id', sa.String(), nullable=True),
    sa.Column('heartbeat_at', sa.String(), nullable=True),
    sa.Column('error_json', sa.JSON(), nullable=True),
    sa.Column('provider_run_ids_json', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.Column('started_at', sa.String(), nullable=True),
    sa.Column('ended_at', sa.String(), nullable=True),
    sa.Column('claim_token', sa.String(), nullable=True),
    sa.CheckConstraint("kind IN ('parse','extract_requirements','extract_materials','verify','supplement','export')", name='kind_values'),
    sa.CheckConstraint("state IN ('queued','running','succeeded','failed','interrupted','cancelled')", name='state_values'),
    sa.CheckConstraint('attempt >= 1', name='job_attempt_positive'),
    sa.ForeignKeyConstraint(['project_id', 'parent_job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_jobs_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id', 'snapshot_id'], ['snapshots.project_id', 'snapshots.id'], name=op.f('fk_jobs_project_id_snapshots')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_jobs_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_jobs_project_id')),
    sa.UniqueConstraint('project_id', 'request_key', name=op.f('uq_jobs_project_id'))
    )
    op.create_index('ix_jobs_claim', 'jobs', ['state', 'created_at'], unique=False)
    op.create_index(op.f('ix_jobs_project_id'), 'jobs', ['project_id'], unique=False)
    op.create_index('ix_jobs_recovery', 'jobs', ['state', 'heartbeat_at'], unique=False)
    op.create_table('review_records',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('target_kind', sa.String(), nullable=False),
    sa.Column('target_id', sa.String(), nullable=False),
    sa.Column('target_revision', sa.Integer(), nullable=True),
    sa.Column('target_content_hash', sa.String(), nullable=False),
    sa.Column('decision', sa.String(), nullable=False),
    sa.Column('note', sa.String(), nullable=False),
    sa.Column('actor_id', sa.String(), nullable=False),
    sa.Column('snapshot_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.CheckConstraint("target_kind IN ('requirement','check')", name='target_kind_values'),
    sa.ForeignKeyConstraint(['project_id', 'snapshot_id'], ['snapshots.project_id', 'snapshots.id'], name=op.f('fk_review_records_project_id_snapshots')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_review_records_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_records')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_review_records_project_id'))
    )
    op.create_index(op.f('ix_review_records_project_id'), 'review_records', ['project_id'], unique=False)
    op.create_index('ix_review_records_target', 'review_records', ['project_id', 'target_kind', 'target_id'], unique=False)
    op.create_table('check_results',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('job_id', sa.String(), nullable=False),
    sa.Column('snapshot_id', sa.String(), nullable=False),
    sa.Column('requirement_id', sa.String(), nullable=False),
    sa.Column('requirement_revision', sa.Integer(), nullable=False),
    sa.Column('check_state', sa.String(), nullable=False),
    sa.Column('condition_results_json', sa.JSON(), nullable=False),
    sa.Column('candidate_ids_json', sa.JSON(), nullable=False),
    sa.Column('evidence_refs_json', sa.JSON(), nullable=False),
    sa.Column('issues_json', sa.JSON(), nullable=False),
    sa.Column('supplement_json', sa.JSON(), nullable=False),
    sa.Column('dependency_hash', sa.String(), nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('is_simulated', sa.Boolean(), nullable=False),
    sa.CheckConstraint("check_state IN ('supported','partial','missing','contradicted','needs_review')", name='check_state_values'),
    sa.ForeignKeyConstraint(['project_id', 'job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_check_results_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id', 'requirement_id', 'requirement_revision'], ['requirements.project_id', 'requirements.requirement_id', 'requirements.revision'], name=op.f('fk_check_results_project_id_requirements')),
    sa.ForeignKeyConstraint(['project_id', 'snapshot_id'], ['snapshots.project_id', 'snapshots.id'], name=op.f('fk_check_results_project_id_snapshots')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_check_results_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_check_results')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_check_results_project_id'))
    )
    op.create_index('ix_check_results_job', 'check_results', ['job_id'], unique=False)
    op.create_index(op.f('ix_check_results_project_id'), 'check_results', ['project_id'], unique=False)
    op.create_table('exports',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('snapshot_id', sa.String(), nullable=False),
    sa.Column('verification_job_id', sa.String(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('artifact_keys_json', sa.JSON(), nullable=False),
    sa.Column('result_bindings_json', sa.JSON(), nullable=False),
    sa.Column('is_simulated', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=False),
    sa.Column('error_json', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['project_id', 'snapshot_id'], ['snapshots.project_id', 'snapshots.id'], name=op.f('fk_exports_project_id_snapshots')),
    sa.ForeignKeyConstraint(['project_id', 'verification_job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_exports_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_exports_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exports')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_exports_project_id'))
    )
    op.create_index(op.f('ix_exports_project_id'), 'exports', ['project_id'], unique=False)
    op.create_table('files',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('logical_file_id', sa.String(), nullable=False),
    sa.Column('version_no', sa.Integer(), nullable=False),
    sa.Column('replaces_file_id', sa.String(), nullable=True),
    sa.Column('source_kind', sa.String(), nullable=False),
    sa.Column('original_name', sa.String(), nullable=False),
    sa.Column('relative_path', sa.String(), nullable=False),
    sa.Column('sha256', sa.String(), nullable=False),
    sa.Column('storage_key', sa.String(), nullable=False),
    sa.Column('active_state', sa.String(), nullable=False),
    sa.Column('parse_state', sa.String(), nullable=False),
    sa.Column('current_parse_job_id', sa.String(), nullable=True),
    sa.Column('error_json', sa.JSON(), nullable=True),
    sa.CheckConstraint("active_state IN ('pending','active','superseded','disabled')", name='active_state_values'),
    sa.CheckConstraint("parse_state IN ('pending','processing','succeeded','partial','failed')", name='parse_state_values'),
    sa.CheckConstraint('version_no >= 1', name='file_version_positive'),
    sa.ForeignKeyConstraint(['project_id', 'current_parse_job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_files_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id', 'replaces_file_id'], ['files.project_id', 'files.id'], name=op.f('fk_files_project_id_files')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_files_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_files')),
    sa.UniqueConstraint('logical_file_id', 'version_no', name=op.f('uq_files_logical_file_id')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_files_project_id'))
    )
    op.create_index(op.f('ix_files_project_id'), 'files', ['project_id'], unique=False)
    op.create_index('ix_files_project_state', 'files', ['project_id', 'active_state'], unique=False)
    op.create_table('materials',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('file_ids_json', sa.JSON(), nullable=False),
    sa.Column('extraction_job_id', sa.String(), nullable=False),
    sa.Column('supersedes_material_id', sa.String(), nullable=True),
    sa.Column('material_type', sa.String(), nullable=False),
    sa.Column('entity_name', sa.String(), nullable=True),
    sa.Column('person_name', sa.String(), nullable=True),
    sa.Column('product_model', sa.String(), nullable=True),
    sa.Column('facts_json', sa.JSON(), nullable=False),
    sa.Column('extraction_state', sa.String(), nullable=False),
    sa.Column('artifact_state', sa.String(), nullable=False),
    sa.Column('content_hash', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['project_id', 'extraction_job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_materials_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id', 'supersedes_material_id'], ['materials.project_id', 'materials.id'], name=op.f('fk_materials_project_id_materials')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_materials_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_materials')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_materials_project_id'))
    )
    op.create_index('ix_materials_current', 'materials', ['project_id', 'artifact_state'], unique=False)
    op.create_index(op.f('ix_materials_project_id'), 'materials', ['project_id'], unique=False)
    op.create_table('source_blocks',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('file_id', sa.String(), nullable=False),
    sa.Column('parse_job_id', sa.String(), nullable=False),
    sa.Column('page_index', sa.Integer(), nullable=False),
    sa.Column('printed_page_label', sa.String(), nullable=True),
    sa.Column('section', sa.String(), nullable=True),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('bbox_json', sa.JSON(), nullable=True),
    sa.Column('method', sa.String(), nullable=False),
    sa.Column('quality_json', sa.JSON(), nullable=False),
    sa.Column('page_image_key', sa.String(), nullable=True),
    sa.CheckConstraint('page_index >= 0', name='page_index_nonnegative'),
    sa.ForeignKeyConstraint(['project_id', 'file_id'], ['files.project_id', 'files.id'], name=op.f('fk_source_blocks_project_id_files')),
    sa.ForeignKeyConstraint(['project_id', 'parse_job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_source_blocks_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_source_blocks_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_blocks')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_source_blocks_project_id'))
    )
    op.create_index('ix_source_blocks_file_parse', 'source_blocks', ['file_id', 'parse_job_id'], unique=False)
    op.create_index(op.f('ix_source_blocks_project_id'), 'source_blocks', ['project_id'], unique=False)
    op.create_table('supplement_operations',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('project_id', sa.String(), nullable=False),
    sa.Column('operation', sa.String(), nullable=False),
    sa.Column('target_file_id', sa.String(), nullable=True),
    sa.Column('new_file_ids_json', sa.JSON(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('job_id', sa.String(), nullable=True),
    sa.Column('base_input_revision', sa.Integer(), nullable=False),
    sa.Column('affected_requirement_ids_json', sa.JSON(), nullable=False),
    sa.Column('request_key', sa.String(), nullable=False),
    sa.Column('error_json', sa.JSON(), nullable=True),
    sa.CheckConstraint("operation != 'replace' OR target_file_id IS NOT NULL", name='replace_requires_target'),
    sa.CheckConstraint("operation IN ('add','replace')", name='operation_values'),
    sa.CheckConstraint("state IN ('pending','processing','committed','rechecking','completed','failed','recheck_failed')", name='state_values'),
    sa.ForeignKeyConstraint(['project_id', 'job_id'], ['jobs.project_id', 'jobs.id'], name=op.f('fk_supplement_operations_project_id_jobs')),
    sa.ForeignKeyConstraint(['project_id', 'target_file_id'], ['files.project_id', 'files.id'], name=op.f('fk_supplement_operations_project_id_files')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_supplement_operations_project_id_projects')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_supplement_operations')),
    sa.UniqueConstraint('project_id', 'id', name=op.f('uq_supplement_operations_project_id')),
    sa.UniqueConstraint('project_id', 'request_key', name=op.f('uq_supplement_operations_project_id'))
    )
    op.create_index(op.f('ix_supplement_operations_project_id'), 'supplement_operations', ['project_id'], unique=False)


def downgrade():
    # Frozen S02 schema; later changes require a new revision.
    op.drop_index(op.f('ix_supplement_operations_project_id'), table_name='supplement_operations')
    op.drop_table('supplement_operations')
    op.drop_index(op.f('ix_source_blocks_project_id'), table_name='source_blocks')
    op.drop_index('ix_source_blocks_file_parse', table_name='source_blocks')
    op.drop_table('source_blocks')
    op.drop_index(op.f('ix_materials_project_id'), table_name='materials')
    op.drop_index('ix_materials_current', table_name='materials')
    op.drop_table('materials')
    op.drop_index('ix_files_project_state', table_name='files')
    op.drop_index(op.f('ix_files_project_id'), table_name='files')
    op.drop_table('files')
    op.drop_index(op.f('ix_exports_project_id'), table_name='exports')
    op.drop_table('exports')
    op.drop_index(op.f('ix_check_results_project_id'), table_name='check_results')
    op.drop_index('ix_check_results_job', table_name='check_results')
    op.drop_table('check_results')
    op.drop_index('ix_review_records_target', table_name='review_records')
    op.drop_index(op.f('ix_review_records_project_id'), table_name='review_records')
    op.drop_table('review_records')
    op.drop_index('ix_jobs_recovery', table_name='jobs')
    op.drop_index(op.f('ix_jobs_project_id'), table_name='jobs')
    op.drop_index('ix_jobs_claim', table_name='jobs')
    op.drop_table('jobs')
    op.drop_index(op.f('ix_snapshots_project_id'), table_name='snapshots')
    op.drop_table('snapshots')
    op.drop_index(op.f('ix_requirements_project_id'), table_name='requirements')
    op.drop_table('requirements')
    op.drop_table('projects')

