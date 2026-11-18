from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool

class Database:
    def __init__(self, url: str):
        parsed = make_url(url)
        sqlite = parsed.get_backend_name() == 'sqlite'
        if sqlite and parsed.database and parsed.database != ':memory:':
            try:
                Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass  # Health remains live; capability probes and API errors report failure.
        options = {'connect_args': {'check_same_thread': False, 'timeout': 10}} if sqlite else {}
        if sqlite and parsed.database == ':memory:':
            options['poolclass'] = StaticPool
        self.engine = create_engine(url, **options)
        self.sqlite = sqlite
        if sqlite:
            @event.listens_for(self.engine, 'connect')
            def configure(connection, _):
                connection.execute('PRAGMA foreign_keys=ON')
                connection.execute('PRAGMA busy_timeout=10000')

    @contextmanager
    def transaction(self):
        with self.engine.connect() as connection:
            try:
                if self.sqlite:
                    connection.exec_driver_sql('BEGIN IMMEDIATE')
                else:
                    connection.begin()
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
