import os
from pathlib import Path
from typing import Any

from libsql_client import create_client, Client

DEFAULT_USER_NAME = "Wojtek"
_SCHEMA_PATH = Path(__file__).with_name("db_schema.sql")
_client: Client | None = None


def _get_db_url() -> str:
    default_path = Path(__file__).resolve().parent.parent / "dechord.db"
    return os.getenv("DECHORD_DB_URL", f"file:{default_path}")


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(_get_db_url())
    return _client


async def execute(sql: str, args: list[Any] | tuple[Any, ...] | None = None):
    client = get_client()
    if args is None:
        return await client.execute(sql)
    return await client.execute(sql, list(args))


async def init_db() -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in schema.split(";") if stmt.strip()]
    for stmt in statements:
        await execute(stmt)
    await get_default_user()


async def get_default_user() -> dict[str, Any]:
    await execute(
        """
        INSERT INTO users (display_name)
        VALUES (?)
        ON CONFLICT(display_name) DO NOTHING
        """,
        [DEFAULT_USER_NAME],
    )
    rs = await execute(
        "SELECT id, display_name FROM users WHERE display_name = ?",
        [DEFAULT_USER_NAME],
    )
    row = rs.rows[0]
    return row.asdict() if hasattr(row, "asdict") else {
        "id": row[0],
        "display_name": row[1],
    }


async def close_db() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def reset_db_client_for_tests() -> None:
    await close_db()
