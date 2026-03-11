import os
import random
from pathlib import Path
from typing import Any

from libsql_client import create_client, Client

DEFAULT_USER_NAME = "Wojtek"
DEFAULT_BAND_NAME = "Default Band"
DEFAULT_PROJECT_NAME = "Default Project"
_SCHEMA_PATH = Path(__file__).with_name("db_schema.sql")
_client: Client | None = None
_MUSICIAN_ADJECTIVES = [
    "Groove",
    "Funky",
    "Silent",
    "Analog",
    "Neon",
    "Velvet",
    "Solar",
    "Midnight",
]
_MUSICIAN_NOUNS = [
    "Bassline",
    "Drummer",
    "Riff",
    "Fret",
    "Metronome",
    "Vocalist",
    "Chord",
    "Octave",
]


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


async def _table_has_column(table_name: str, column_name: str) -> bool:
    rs = await execute(f"PRAGMA table_info({table_name})")
    return any(str(row[1]) == column_name for row in rs.rows)


async def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    if await _table_has_column(table_name, column_name):
        return
    await execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


async def _run_schema_migrations() -> None:
    await _ensure_column(
        "song_stems",
        "source_type",
        "source_type TEXT NOT NULL DEFAULT 'system'",
    )
    await _ensure_column("song_stems", "display_name", "display_name TEXT")
    await _ensure_column(
        "song_stems",
        "version_label",
        "version_label TEXT NOT NULL DEFAULT 'legacy'",
    )
    await _ensure_column(
        "song_stems",
        "uploaded_by_name",
        "uploaded_by_name TEXT",
    )
    await _ensure_column("song_midis", "source_stem_id", "source_stem_id INTEGER")
    await _ensure_column(
        "song_midis",
        "source_stem_source_type",
        "source_stem_source_type TEXT NOT NULL DEFAULT 'system'",
    )
    await _ensure_column(
        "song_midis",
        "source_stem_display_name",
        "source_stem_display_name TEXT",
    )
    await _ensure_column(
        "song_midis",
        "source_stem_version_label",
        "source_stem_version_label TEXT",
    )
    await _ensure_column(
        "song_midis",
        "source_stem_uploaded_by_name",
        "source_stem_uploaded_by_name TEXT",
    )


async def init_db() -> None:
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in schema.split(";") if stmt.strip()]
    for stmt in statements:
        await execute(stmt)
    await _run_schema_migrations()
    await get_default_project()


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
    return (
        row.asdict()
        if hasattr(row, "asdict")
        else {
            "id": row[0],
            "display_name": row[1],
        }
    )


def _generate_guest_display_name() -> str:
    return f"{random.choice(_MUSICIAN_ADJECTIVES)} {random.choice(_MUSICIAN_NOUNS)}"


def _row_as_user_dict(row: Any) -> dict[str, Any]:
    data = (
        row.asdict()
        if hasattr(row, "asdict")
        else {
            "id": row[0],
            "display_name": row[1],
            "fingerprint_token": row[2],
            "username": row[3],
            "is_claimed": row[4],
        }
    )
    return {
        "id": int(data["id"]),
        "display_name": data["display_name"],
        "fingerprint_token": data.get("fingerprint_token"),
        "username": data.get("username"),
        "is_claimed": bool(data.get("is_claimed", 0)),
    }


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    rs = await execute(
        """
        SELECT id, display_name, fingerprint_token, username, is_claimed
        FROM users
        WHERE id = ?
        """,
        [user_id],
    )
    if not rs.rows:
        return None
    return _row_as_user_dict(rs.rows[0])


async def resolve_identity_user(fingerprint_token: str) -> dict[str, Any]:
    existing = await execute(
        """
        SELECT id, display_name, fingerprint_token, username, is_claimed
        FROM users
        WHERE fingerprint_token = ?
        """,
        [fingerprint_token],
    )
    if existing.rows:
        return _row_as_user_dict(existing.rows[0])

    for _ in range(10):
        display_name = _generate_guest_display_name()
        await execute(
            """
            INSERT INTO users (display_name, fingerprint_token, is_claimed)
            VALUES (?, ?, 0)
            ON CONFLICT(display_name) DO NOTHING
            """,
            [display_name, fingerprint_token],
        )
        created = await execute(
            """
            SELECT id, display_name, fingerprint_token, username, is_claimed
            FROM users
            WHERE fingerprint_token = ?
            """,
            [fingerprint_token],
        )
        if created.rows:
            return _row_as_user_dict(created.rows[0])

    raise RuntimeError("Failed to allocate guest identity")


async def claim_identity_user(
    user_id: int, username: str, password_hash: str
) -> dict[str, Any] | None:
    await execute(
        """
        UPDATE users
        SET username = ?, is_claimed = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        [username, user_id],
    )
    await execute(
        """
        INSERT INTO user_credentials (user_id, password_hash)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            password_hash = excluded.password_hash,
            updated_at = CURRENT_TIMESTAMP
        """,
        [user_id, password_hash],
    )
    return await get_user_by_id(user_id)


async def get_default_project() -> dict[str, Any]:
    user = await get_default_user()
    await execute(
        """
        INSERT INTO bands (name, owner_user_id)
        VALUES (?, ?)
        ON CONFLICT(name, owner_user_id) DO NOTHING
        """,
        [DEFAULT_BAND_NAME, user["id"]],
    )
    band_rs = await execute(
        "SELECT id, name FROM bands WHERE name = ? AND owner_user_id = ?",
        [DEFAULT_BAND_NAME, user["id"]],
    )
    band_row = band_rs.rows[0]
    band_id = int(band_row[0])

    await execute(
        """
        INSERT INTO band_memberships (band_id, user_id, role)
        VALUES (?, ?, 'owner')
        ON CONFLICT(band_id, user_id) DO UPDATE SET
            role = 'owner',
            updated_at = CURRENT_TIMESTAMP
        """,
        [band_id, user["id"]],
    )

    await execute(
        """
        INSERT INTO projects (band_id, name, description)
        VALUES (?, ?, ?)
        ON CONFLICT(band_id, name) DO NOTHING
        """,
        [
            band_id,
            DEFAULT_PROJECT_NAME,
            "Default project created for local development.",
        ],
    )
    project_rs = await execute(
        "SELECT id, name, band_id FROM projects WHERE band_id = ? AND name = ?",
        [band_id, DEFAULT_PROJECT_NAME],
    )
    row = project_rs.rows[0]
    return {
        "id": int(row[0]),
        "name": row[1],
        "band_id": int(row[2]),
    }


async def close_db() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def reset_db_client_for_tests() -> None:
    await close_db()
