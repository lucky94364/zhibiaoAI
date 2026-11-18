from sqlalchemy import select, update, insert
from app.models import projects
from app.services.common import DomainError, now, new_id, digest, require_replay


def project_view(row):
    return dict(project_id=row['id'], name=row['name'], context=row['context_json'], scope=row['scope_json'],
                input_revision=row['input_revision'], state=row['state'],
                current_verification_job_id=row['current_verification_job_id'],
                created_at=row['created_at'], updated_at=row['updated_at'])


def get_project(connection, project_id, lock=False):
    query = select(projects).where(projects.c.id == project_id)
    row = connection.execute(query.with_for_update() if lock else query).mappings().first()
    if row is None:
        raise DomainError('RESOURCE_NOT_FOUND', '项目不存在', 404)
    return row


class ProjectService:
    def __init__(self, database):
        self.db = database

    def create(self, body, key, actor):
        payload = body.model_dump(mode='json')
        request_hash = digest({'body': payload, 'actor': actor})
        with self.db.transaction() as connection:
            previous = connection.execute(select(projects).where(projects.c.create_request_key == key)).mappings().first()
            if previous:
                return require_replay({'hash': previous['create_request_hash'], 'response': previous['create_response_json']}, request_hash)
            row = dict(id=new_id('PRJ'), name=payload['name'], context_json=payload['context'], scope_json=payload['scope'],
                       input_revision=1, state='preparing', current_verification_job_id=None, decision_json=None,
                       created_at=now(), updated_at=now(), create_request_key=key, create_request_hash=request_hash,
                       operation_records_json={})
            response = project_view(row)
            connection.execute(insert(projects).values(**row, create_response_json=response))
            return response

    def get(self, project_id):
        with self.db.engine.connect() as connection:
            return project_view(get_project(connection, project_id))

    def list(self):
        with self.db.engine.connect() as connection:
            rows = connection.execute(select(projects).order_by(projects.c.created_at, projects.c.id)).mappings()
            items = [project_view(row) for row in rows]
            return {'items': items, 'total': len(items)}

    def patch(self, project_id, body, key, actor):
        payload = body.model_dump(mode='json', exclude_unset=True)
        request_hash = digest({'body': payload, 'actor': actor})
        ledger_key = 'patch:' + key
        with self.db.transaction() as connection:
            row = get_project(connection, project_id, lock=True)
            ledger = dict(row['operation_records_json'])
            if ledger_key in ledger:
                return require_replay(ledger[ledger_key], request_hash)
            expected = body.expected_input_revision
            if expected != row['input_revision']:
                raise DomainError('VERSION_CONFLICT', '项目输入版本已变化，请刷新重试', details={'expected': expected, 'current': row['input_revision']})
            changes = {}
            for field in ('name', 'context', 'scope'):
                column = field + '_json' if field != 'name' else field
                if field in payload and payload[field] != row[column]:
                    changes[column] = payload[field]
            # All context/scope changes conservatively invalidate current bindings.
            if 'context_json' in changes or 'scope_json' in changes:
                changes.update(input_revision=expected + 1, current_verification_job_id=None)
                if row['state'] not in ('abandoned', 'archived'):
                    changes['state'] = 'preparing'
            if changes:
                changes['updated_at'] = now()
            response = project_view({**row, **changes})
            ledger[ledger_key] = {'hash': request_hash, 'response': response}
            changes['operation_records_json'] = ledger
            result = connection.execute(update(projects).where(projects.c.id == project_id, projects.c.input_revision == expected).values(**changes))
            if result.rowcount != 1:
                raise DomainError('VERSION_CONFLICT', '项目输入版本已变化')
            return response
