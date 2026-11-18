import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from sqlalchemy import select, update, insert, inspect
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from app.models import metadata, projects, jobs, snapshots, files, source_blocks, review_records
from app.repositories.database import Database
from app.schemas.core import ProjectCreate, Context, Snapshot
from app.services.common import DomainError, now
from app.services.idempotency import perform_once
from app.services.projects import ProjectService
from app.settings import Settings, PROJECT_ROOT
from app.tasks.store import JobStore
from app.tasks.worker import run_once

BODY = {'name': '材料核验项目', 'context': {'bidder_name': '测试公司', 'project_leader': '负责人', 'deadline': '2026-11-30T01:00:00Z', 'timezone': 'Asia/Shanghai'}, 'scope': {'label': 'Q01-Q04'}}


def migrate(url, target='head'):
    config = Config(str(PROJECT_ROOT / 'backend/alembic.ini'))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('ZB_DATABASE_URL', url)
        command.upgrade(config, target)


@pytest.fixture
def env(tmp_path):
    url = f'sqlite:///{tmp_path}/db.sqlite'
    migrate(url)
    settings = Settings(_env_file=None, database_url=url, storage_dir=tmp_path / 'storage')
    db = Database(url)
    app = create_app(settings)
    with TestClient(app) as client:
        yield db, client, settings
    db.engine.dispose()


def create(client, key='create-key'):
    response = client.post('/api/v1/projects', json=BODY, headers={'Idempotency-Key': key})
    assert response.status_code == 201, response.text
    return response.json()


def validate(name, value):
    schema = json.loads((PROJECT_ROOT / 'docs/current/contracts/domain.schema.json').read_text())
    Draft202012Validator({**schema, '$ref': f'#/$defs/{name}'}).validate(value)


def test_migration_eleven_tables_and_roundtrip(tmp_path):
    url = f'sqlite:///{tmp_path}/empty.db'
    migrate(url)
    db = Database(url)
    assert set(inspect(db.engine).get_table_names()) == set(metadata.tables) | {'alembic_version'}
    assert len(metadata.tables) == 11
    config = Config(str(PROJECT_ROOT / 'backend/alembic.ini'))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('ZB_DATABASE_URL', url)
        command.downgrade(config, 'base')
    assert inspect(db.engine).get_table_names() == ['alembic_version']
    migrate(url)
    db.engine.dispose()


def test_project_replay_restart_and_contract(env):
    db, client, settings = env
    first = create(client)
    assert create(client) == first
    validate('Project', first)
    validate('ProjectList', client.get('/api/v1/projects').json())
    db.engine.dispose()
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/api/v1/projects/' + first['project_id']).json() == first
        assert restarted.get('/api/v1/projects').json()['total'] == 1
    conflict = client.post('/api/v1/projects', json={**BODY, 'name': 'changed'}, headers={'Idempotency-Key': 'create-key'})
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    validate('Error', conflict.json())


def test_patch_revision_invalidation_and_history(env):
    db, client, _ = env
    project = create(client)
    pid = project['project_id']
    store = JobStore(db)
    accepted = store.enqueue(pid, 'verify', {}, 'existing')
    with db.transaction() as connection:
        connection.execute(update(projects).where(projects.c.id == pid).values(current_verification_job_id=accepted['job_id'], state='ready_in_scope'))
        connection.execute(insert(review_records).values(id='REV-history', project_id=pid, target_kind='check', target_id='historical-check', target_revision=None, target_content_hash='hash', decision='confirmed', note='', actor_id='tester', snapshot_id=None, created_at=now()))
    body = {'expected_input_revision': 1, 'context': {**BODY['context'], 'project_leader': '新负责人'}}
    url = '/api/v1/projects/' + pid
    response = client.patch(url, json=body, headers={'Idempotency-Key': 'patch-1'})
    assert response.status_code == 200
    current = response.json()
    assert current['input_revision'] == 2 and current['state'] == 'preparing'
    assert current['current_verification_job_id'] is None
    assert client.patch(url, json=body, headers={'Idempotency-Key': 'patch-1'}).json() == current
    assert client.patch(url, json={**body, 'name': 'different'}, headers={'Idempotency-Key': 'patch-1'}).json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert client.patch(url, json=body, headers={'Idempotency-Key': 'patch-old'}).json()['error']['code'] == 'VERSION_CONFLICT'
    with db.engine.connect() as connection:
        assert connection.execute(select(review_records)).mappings().one()['decision'] == 'confirmed'
        assert connection.execute(select(jobs)).mappings().one()['id'] == accepted['job_id']
    renamed = client.patch(url, json={'expected_input_revision': 2, 'name': '新名称'}, headers={'Idempotency-Key': 'rename'}).json()
    assert renamed['input_revision'] == 2
    # Replaying creation returns the original response, not the subsequently updated project.
    assert create(client) == project


def test_concurrent_project_operations(env):
    db, client, _ = env
    service = ProjectService(db)
    body = ProjectCreate.model_validate(BODY)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: service.create(body, 'parallel', 'tester'), range(4)))
    assert len({r['project_id'] for r in responses}) == 1
    assert service.list()['total'] == 1
    pid = responses[0]['project_id']
    def patch(index):
        from app.schemas.core import ProjectPatch
        try:
            return service.patch(pid, ProjectPatch(expected_input_revision=1, scope={'label': str(index)}), f'patch-{index}', 'tester')['input_revision']
        except DomainError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(patch, range(2)))
    assert sorted(map(str, results)) == ['2', 'VERSION_CONFLICT']


def test_validation_errors_and_timezone(env):
    _, client, _ = env
    assert client.post('/api/v1/projects', json=BODY).status_code == 422
    for context in [{**BODY['context'], 'timezone': 'not/a_zone'}, {**BODY['context'], 'deadline': '2026-11-30T01:00:00'}, {**BODY['context'], 'deadline_date': '2026-11-30'}]:
        assert client.post('/api/v1/projects', json={**BODY, 'context': context}, headers={'Idempotency-Key': 'invalid'}).status_code == 422
    project = create(client)
    for field in ['name', 'context', 'scope']:
        assert client.patch('/api/v1/projects/' + project['project_id'], json={'expected_input_revision': 1, field: None}, headers={'Idempotency-Key': 'null'}).status_code == 422
    assert Context.model_validate({**BODY['context'], 'deadline': '2026-11-29T23:30:00Z'}).deadline_date.isoformat() == '2026-11-30'
    for path in ['/projects/missing', '/jobs/missing']:
        response = client.get('/api/v1' + path)
        assert response.status_code == 404
        validate('Error', response.json())
    response = client.options('/api/v1/projects', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert response.status_code == 200


def test_jobs_claim_progress_recovery_and_fencing(env):
    db, client, _ = env
    pid = create(client)['project_id']
    store = JobStore(db)
    accepted = store.enqueue(pid, 'parse', {'file_id': 'future'}, 'parse-1')
    validate('JobAccepted', accepted)
    assert store.enqueue(pid, 'parse', {'file_id': 'future'}, 'parse-1') == accepted
    with pytest.raises(DomainError, match='同一幂等键'):
        store.enqueue(pid, 'parse', {'file_id': 'other'}, 'parse-1')
    with ThreadPoolExecutor(max_workers=3) as pool:
        claimed = list(pool.map(lambda _: store.claim(), range(3)))
    job = next(item for item in claimed if item)
    assert sum(item is not None for item in claimed) == 1
    store.progress(job['id'], job['claim_token'], {'stage': 'reading', 'completed': 1})
    assert store.get(job['id'])['progress']['completed'] == 1
    assert store.recover() == 0
    with db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == job['id']).values(heartbeat_at=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()))
    assert store.recover() == 1
    response = client.get('/api/v1/jobs/' + job['id'])
    validate('Job', response.json())
    assert response.json()['state'] == 'interrupted'
    assert response.json()['output'] is None
    with pytest.raises(DomainError):
        store.finish(job['id'], job['claim_token'], {'stale': True})
    with pytest.raises(DomainError):
        store.progress(job['id'], job['claim_token'], {'stale': True})
    retry_url = '/api/v1/jobs/' + job['id'] + '/retry'
    retry = client.post(retry_url, headers={'Idempotency-Key': 'retry-1'})
    assert retry.status_code == 202
    assert client.post(retry_url, headers={'Idempotency-Key': 'retry-1'}).json() == retry.json()
    assert client.post(retry_url, headers={'Idempotency-Key': 'retry-2'}).status_code == 409
    retried = store.get(retry.json()['job_id'])
    assert retried['attempt'] == 2 and retried['parent_job_id'] == job['id']
    assert store.get(job['id'])['state'] == 'interrupted'
    # Unimplemented handlers fail honestly, with no fabricated successful output.
    assert run_once(store)
    assert store.get(retried['job_id'])['error']['code'] == 'JOB_HANDLER_UNAVAILABLE'
    assert store.get(retried['job_id'])['output'] is None
    assert store.enqueue(pid, 'parse', {'file_id': 'future'}, 'parse-1') == accepted


def test_worker_handler_and_transactional_side_effect_once(env):
    db, client, _ = env
    pid = create(client)['project_id']
    store = JobStore(db)
    accepted = store.enqueue(pid, 'parse', {}, 'test-handler')
    calls = []
    def effect(connection):
        calls.append('effect')
        connection.execute(update(projects).where(projects.c.id == pid).values(name='effect committed'))
        return {'done': True}
    with pytest.raises(RuntimeError):
        with db.transaction() as connection:
            perform_once(connection, pid, 'test', 'stable-operation', {}, effect)
            raise RuntimeError('rollback')
    assert ProjectService(db).get(pid)['name'] == BODY['name']
    calls.clear()
    def handler(job, progress):
        progress({'checkpoint': 'start'})
        with db.transaction() as connection:
            return perform_once(connection, pid, 'test', 'stable-operation', {}, effect)
    run_once(store, {'parse': handler})
    assert store.get(accepted['job_id'])['state'] == 'succeeded'
    # Same business operation from another attempt has no duplicate effect.
    with db.transaction() as connection:
        assert perform_once(connection, pid, 'test', 'stable-operation', {}, effect) == {'done': True}
    assert calls == ['effect']
    with pytest.raises(DomainError):
        with db.transaction() as connection:
            perform_once(connection, pid, 'test', 'stable-operation', {'changed': True}, effect)


def test_cross_project_fk_and_snapshot_type(env):
    db, client, _ = env
    first = create(client)['project_id']
    second = create(client, 'second')['project_id']
    job_id = JobStore(db).enqueue(first, 'parse', {}, 'job')['job_id']
    snapshot = Snapshot(id='SNP-test', project_id=first, input_revision=1, context=BODY['context'], scope=BODY['scope'], requirement_versions=[], active_file_ids=[], active_material_ids=[], coverage={'state': 'not_processed'}, hash='test-only', created_at=now())
    assert snapshot.coverage['state'] == 'not_processed'
    with pytest.raises(Exception):
        snapshot.input_revision = 2
    with pytest.raises(IntegrityError):
        with db.transaction() as connection:
            connection.execute(insert(files).values(id='DOC-cross', project_id=second, logical_file_id='logical', version_no=1, replaces_file_id=None, source_kind='material', original_name='a.pdf', relative_path='a.pdf', sha256='hash', storage_key='key', active_state='pending', parse_state='pending', current_parse_job_id=job_id, error_json=None))
    with db.engine.connect() as connection:
        assert connection.execute(select(files)).first() is None
    with pytest.raises(DomainError):
        JobStore(db).enqueue(second, 'verify', {}, 'invalid-snapshot', snapshot_id='nonexistent')


def test_worker_process_recovery_and_failure_are_durable(env):
    import os
    import subprocess
    import sys
    db, client, settings = env
    pid = create(client)['project_id']
    store = JobStore(db)
    accepted = store.enqueue(pid, 'parse', {'checkpoint_key': 'stable'}, 'process-job')
    claim = store.claim()
    with db.transaction() as connection:
        connection.execute(update(jobs).where(jobs.c.id == claim['id']).values(heartbeat_at='2020-01-01T00:00:00+00:00'))
    process_env = {**os.environ, 'ZB_DATABASE_URL': settings.database_url}
    command_line = [sys.executable, '-m', 'app.tasks.worker']
    subprocess.run(command_line + ['--recover-only'], cwd=PROJECT_ROOT / 'backend', env=process_env, check=True, capture_output=True)
    assert store.get(accepted['job_id'])['state'] == 'interrupted'
    assert store.get(accepted['job_id'])['output'] is None
    retried = store.retry(accepted['job_id'], 'subprocess-retry', 'tester')
    subprocess.run(command_line + ['--once'], cwd=PROJECT_ROOT / 'backend', env=process_env, check=True, capture_output=True)
    response = client.get('/api/v1/jobs/' + retried['job_id'])
    assert response.json()['state'] == 'failed'
    assert response.json()['error']['code'] == 'JOB_HANDLER_UNAVAILABLE'
    with db.engine.connect() as connection:
        original = connection.execute(select(jobs).where(jobs.c.id == accepted['job_id'])).mappings().one()
        retry = connection.execute(select(jobs).where(jobs.c.id == retried['job_id'])).mappings().one()
        assert original['input_json'] == retry['input_json']


def test_file_version_unique_and_transaction_rollback(env):
    db, client, _ = env
    pid = create(client)['project_id']
    base = dict(project_id=pid, logical_file_id='same-logical', version_no=1, replaces_file_id=None, source_kind='material', original_name='same.pdf', relative_path='same.pdf', sha256='hash', storage_key='key', active_state='pending', parse_state='pending', current_parse_job_id=None, error_json=None)
    with pytest.raises(IntegrityError):
        with db.transaction() as connection:
            connection.execute(insert(files).values(id='DOC-one', **base))
            connection.execute(insert(files).values(id='DOC-two', **base))
    with db.engine.connect() as connection:
        assert connection.execute(select(files)).first() is None


def test_retry_does_not_repeat_committed_side_effect(env):
    db, client, _ = env
    pid = create(client)['project_id']
    store = JobStore(db)
    accepted = store.enqueue(pid, 'parse', {}, 'crash-test')
    calls = []
    def effect(connection):
        calls.append('committed-once')
        connection.execute(update(projects).where(projects.c.id == pid).values(name='one effect'))
        return {'artifact': 'stable-operation-result'}
    def handler(job, progress):
        with db.transaction() as connection:
            output = perform_once(connection, pid, 'artifact', 'stable-key', {}, effect)
        if job['attempt'] == 1:
            raise RuntimeError('failure after side effect commit, before task completion')
        return output
    run_once(store, {'parse': handler})
    assert store.get(accepted['job_id'])['state'] == 'failed'
    retry = store.retry(accepted['job_id'], 'retry-after-commit', 'tester')
    run_once(store, {'parse': handler})
    assert store.get(retry['job_id'])['state'] == 'succeeded'
    assert calls == ['committed-once']
