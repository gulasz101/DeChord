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
