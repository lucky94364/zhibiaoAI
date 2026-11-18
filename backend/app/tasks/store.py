from datetime import datetime, timedelta, timezone
from sqlalchemy import select, insert, update, or_
from app.models import jobs, snapshots
from app.schemas.core import JobKind
from pydantic import TypeAdapter
from app.services.projects import get_project
from app.services.common import DomainError, digest, now, new_id, require_replay


def job_view(row):
    return dict(job_id=row['id'], project_id=row['project_id'], kind=row['kind'], state=row['state'],
                snapshot_id=row['snapshot_id'], progress=row['progress_json'], output=row['output_json'],
                error=row['error_json'], attempt=row['attempt'], parent_job_id=row['parent_job_id'])


def find_job(connection, job_id):
    row = connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().first()
    if row is None:
        raise DomainError('RESOURCE_NOT_FOUND', '任务不存在', 404)
    return row


class JobStore:
    def __init__(self, database):
        self.db = database

    def enqueue(self, project_id, kind, payload, request_key, snapshot_id=None):
        TypeAdapter(JobKind).validate_python(kind)
        with self.db.transaction() as connection:
            get_project(connection, project_id, lock=True)
            return self._enqueue(connection, project_id, kind, payload, request_key, snapshot_id)

    def _enqueue(self, connection, project_id, kind, payload, key, snapshot_id=None, parent=None, attempt=1, actor=None):
        request_hash = digest({'kind': kind, 'input': payload, 'snapshot_id': snapshot_id, 'parent': parent, 'actor': actor})
        previous = connection.execute(select(jobs).where(jobs.c.project_id == project_id, jobs.c.request_key == key)).mappings().first()
        if previous:
            # Always return the original acceptance, even after the job has finished.
            return require_replay({'hash': previous['request_hash'], 'response': {'job_id': previous['id'], 'state': 'queued', 'snapshot_id': previous['snapshot_id']}}, request_hash)
        if snapshot_id:
            snapshot = connection.execute(select(snapshots).where(snapshots.c.id == snapshot_id, snapshots.c.project_id == project_id)).first()
            if snapshot is None:
                raise DomainError('RESOURCE_NOT_FOUND', '当前项目的快照不存在', 404)
        job_id = new_id('JOB')
        connection.execute(insert(jobs).values(id=job_id, project_id=project_id, kind=kind, snapshot_id=snapshot_id,
            request_key=key, request_hash=request_hash, state='queued', progress_json={}, input_json=payload,
            output_json=None, attempt=attempt, parent_job_id=parent, heartbeat_at=None, error_json=None,
            provider_run_ids_json=[], created_at=now(), started_at=None, ended_at=None, claim_token=None))
        return {'job_id': job_id, 'state': 'queued', 'snapshot_id': snapshot_id}

    def get(self, job_id):
        with self.db.engine.connect() as connection:
            return job_view(find_job(connection, job_id))

    def retry(self, job_id, key, actor):
        with self.db.transaction() as connection:
            parent = find_job(connection, job_id)
            get_project(connection, parent['project_id'], lock=True)
            if parent['state'] not in ('failed', 'interrupted'):
                raise DomainError('INPUT_NOT_READY', '仅失败或中断任务可以重试')
            request_key = 'retry:' + key
            previous = connection.execute(select(jobs).where(jobs.c.project_id == parent['project_id'], jobs.c.request_key == request_key)).mappings().first()
            child = connection.execute(select(jobs.c.id).where(jobs.c.parent_job_id == job_id)).first()
            if child and previous is None:
                raise DomainError('VERSION_CONFLICT', '该任务已有重试，请查询重试任务')
            # Preserve input/checkpoints; handlers must perform side effects with their own guarded transaction.
            payload = dict(parent['input_json'])
            return self._enqueue(connection, parent['project_id'], parent['kind'], payload, request_key,
                                 parent['snapshot_id'], parent=job_id, attempt=parent['attempt'] + 1, actor=actor)

    def claim(self):
        with self.db.transaction() as connection:
            # S02 supports one serial worker. CAS below also fences competing claimers.
            if connection.execute(select(jobs.c.id).where(jobs.c.state == 'running').limit(1)).first():
                return None
            row = connection.execute(select(jobs).where(jobs.c.state == 'queued').order_by(jobs.c.created_at, jobs.c.id).limit(1)).mappings().first()
            if row is None:
                return None
            token = new_id('CLAIM')
            changes = dict(state='running', started_at=now(), heartbeat_at=now(), claim_token=token)
            result = connection.execute(update(jobs).where(jobs.c.id == row['id'], jobs.c.state == 'queued').values(**changes))
            return {**row, **changes} if result.rowcount == 1 else None

    def progress(self, job_id, token, progress=None):
        with self.db.transaction() as connection:
            values = {'heartbeat_at': now()}
            if progress is not None:
                values['progress_json'] = progress
            result = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.state == 'running', jobs.c.claim_token == token).values(**values))
            if result.rowcount != 1:
                raise DomainError('VERSION_CONFLICT', '任务领取权已失效')

    def finish(self, job_id, token, output=None, error=None, interrupted=False):
        with self.db.transaction() as connection:
            result = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.state == 'running', jobs.c.claim_token == token).values(
                state='interrupted' if interrupted else ('failed' if error else 'succeeded'), output_json=output,
                error_json=error, ended_at=now(), heartbeat_at=now(), claim_token=None))
            if result.rowcount != 1:
                raise DomainError('VERSION_CONFLICT', '任务领取权已失效，禁止旧任务提交')

    def recover(self, stale_seconds=300):
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).isoformat(timespec='microseconds')
        with self.db.transaction() as connection:
            result = connection.execute(update(jobs).where(jobs.c.state == 'running', or_(jobs.c.heartbeat_at < cutoff, jobs.c.heartbeat_at.is_(None))).values(
                state='interrupted', ended_at=now(), claim_token=None,
                error_json={'code': 'WORKER_INTERRUPTED', 'message': '任务心跳过期；需明确重试，未自动重复副作用'}))
            return result.rowcount
