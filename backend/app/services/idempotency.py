"""Transactional side-effect guard for later file/confirmation/export handlers."""
from sqlalchemy import update
from app.models import projects
from app.services.projects import get_project
from app.services.common import digest, require_replay


def perform_once(connection, project_id, operation, key, payload, action):
    """action(connection) and its JSON result commit or roll back together.

    The caller must use Database.transaction; action must not call OCR/network APIs.
    Scope keys to a stable business operation, including across job retries.
    """
    row = get_project(connection, project_id, lock=True)
    ledger = dict(row['operation_records_json'])
    ledger_key = f'effect:{operation}:{key}'
    request_hash = digest(payload)
    if ledger_key in ledger:
        return require_replay(ledger[ledger_key], request_hash)
    response = action(connection)
    ledger[ledger_key] = {'hash': request_hash, 'response': response}
    connection.execute(update(projects).where(projects.c.id == project_id).values(operation_records_json=ledger))
    return response
