import asyncio
from pathlib import Path

from app import db


def test_db_module_exposes_bootstrap_symbols():
    assert hasattr(db, "init_db")
    assert hasattr(db, "get_default_user")


def test_init_db_creates_default_user(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "dechord-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    asyncio.run(db.reset_db_client_for_tests())
    asyncio.run(db.init_db())
    user = asyncio.run(db.get_default_user())

    assert user["display_name"] == "Wojtek"
    assert user["id"] > 0

    asyncio.run(db.close_db())


def test_init_db_creates_song_stems_table_and_index(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "dechord-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    asyncio.run(db.reset_db_client_for_tests())
    asyncio.run(db.init_db())

    table_rows = asyncio.run(
        db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'song_stems'"
        )
    )
    assert len(table_rows.rows) == 1

    index_rows = asyncio.run(
        db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_song_stems_song_id'"
        )
    )
    assert len(index_rows.rows) == 1

    asyncio.run(db.close_db())


def test_init_db_creates_song_midis_and_song_tabs_tables(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "dechord-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    asyncio.run(db.reset_db_client_for_tests())
    asyncio.run(db.init_db())

    for table_name in ("song_midis", "song_tabs"):
        table_rows = asyncio.run(
            db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                [table_name],
            )
        )
        assert len(table_rows.rows) == 1

    for index_name in ("idx_song_midis_song_id", "idx_song_tabs_song_id"):
        index_rows = asyncio.run(
            db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?",
                [index_name],
            )
        )
        assert len(index_rows.rows) == 1

    asyncio.run(db.close_db())


def test_init_db_creates_collaboration_tables(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "dechord-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    asyncio.run(db.reset_db_client_for_tests())
    asyncio.run(db.init_db())

    required_tables = (
        "users",
        "user_credentials",
        "bands",
        "band_memberships",
        "projects",
        "songs",
    )
    for table_name in required_tables:
        table_rows = asyncio.run(
            db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
                [table_name],
            )
        )
        assert len(table_rows.rows) == 1

    asyncio.run(db.close_db())


def test_songs_table_is_project_scoped(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "dechord-test.db"
    monkeypatch.setenv("DECHORD_DB_URL", f"file:{db_path}")

    asyncio.run(db.reset_db_client_for_tests())
    asyncio.run(db.init_db())

    columns = asyncio.run(db.execute("PRAGMA table_info(songs)"))
    column_names = {row[1] for row in columns.rows}
    assert "project_id" in column_names

    foreign_keys = asyncio.run(db.execute("PRAGMA foreign_key_list(songs)"))
    fk_targets = {row[2] for row in foreign_keys.rows}
    assert "projects" in fk_targets

    asyncio.run(db.close_db())
