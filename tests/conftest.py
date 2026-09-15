import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import db as db_module
from src.main import app

ORIGINAL_DB = Path(__file__).resolve().parent.parent / "gym.db"


@pytest.fixture()
def test_db_path(tmp_path):
    test_db = tmp_path / "gym-test.db"
    shutil.copy(ORIGINAL_DB, test_db)
    return test_db


@pytest.fixture()
def client(monkeypatch, test_db_path):
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    return TestClient(app)
