from alembic import context
from sqlalchemy import create_engine
from app.settings import Settings

from app.models import metadata
target_metadata = metadata
url = Settings().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url)
    from sqlalchemy.engine import make_url
    from pathlib import Path
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
