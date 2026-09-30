import uuid

from sqlalchemy import CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID


class GUID(TypeDecorator):
    """A UUID column that's a native `uuid` on Postgres (production, via
    Render) and a plain CHAR(36) string on any other dialect — specifically
    SQLite, used for local dev/tests where a real Postgres server isn't
    available. Keeps the models themselves free of a hard Postgres
    dependency without changing any production behavior."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)
