"""PostgreSQL connections with identical transaction semantics on both runtimes."""
import os
import ssl
from contextlib import contextmanager
from urllib.parse import unquote, urlsplit


@contextmanager
def connect(database_url):
    if os.environ.get("EDNAI_DATABASE_DRIVER") != "pg8000":
        import psycopg
        with psycopg.connect(database_url) as connection:
            yield connection
        return
    import pg8000.dbapi
    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise ValueError("A PostgreSQL connection URL is required")
    if os.environ.get("EDNAI_WORKERS") == "true":
        from server.worker_socket import WorkerSocket
        transport = {"sock": WorkerSocket(parsed.hostname, parsed.port or 5432), "ssl_context": False}
    else:
        transport = {"ssl_context": ssl.create_default_context()}
    connection = pg8000.dbapi.connect(
        host=parsed.hostname, port=parsed.port or 5432,
        user=unquote(parsed.username or ""), password=unquote(parsed.password or ""),
        database=unquote(parsed.path.lstrip("/")),
        timeout=30, **transport,
    )

    class Transaction:
        @contextmanager
        def cursor(self):
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    try:
        yield Transaction()
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
