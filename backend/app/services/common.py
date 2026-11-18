import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def new_id(prefix):
    return f'{prefix}-{uuid4()}'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class DomainError(Exception):
    def __init__(self, code, message, status=409, details=None):
        self.code, self.message, self.status, self.details = code, message, status, details or {}


def require_replay(record, request_hash):
    if record['hash'] != request_hash:
        raise DomainError('IDEMPOTENCY_CONFLICT', '同一幂等键的请求内容不同')
    return record['response']
