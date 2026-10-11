import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import booking
from src import db as db_module
from src.main import app

ORIGINAL_DB = Path(__file__).resolve().parent.parent / "gym.db"
# Les créneaux du jeu de données commencent le 2026-10-05 : on fige "maintenant" juste avant,
# pour que les tests donnent le même résultat quel que soit le jour où on les lance.
MAINTENANT_FIXE = datetime(2026, 10, 1, tzinfo=timezone.utc)

TOKEN_COACH = "coach-de-test"
TOKEN_ADHERENT = "adherent-de-test"
ADHERENT_ID = 6


@pytest.fixture()
def test_db_path(tmp_path):
    test_db = tmp_path / "gym-test.db"
    shutil.copy(ORIGINAL_DB, test_db)
    return test_db


@pytest.fixture()
def api(monkeypatch, test_db_path):
    """API prête à tester : base temporaire, heure fixe, tokens connus."""
    monkeypatch.setattr(db_module, "DB_PATH", test_db_path)
    monkeypatch.setattr(booking, "utc_now", lambda: MAINTENANT_FIXE)
    monkeypatch.setenv("TOKEN_COACH", TOKEN_COACH)
    monkeypatch.setenv("TOKEN_ADHERENT", TOKEN_ADHERENT)
    monkeypatch.setenv("ADHERENT_ID", str(ADHERENT_ID))
    return app


@pytest.fixture()
def client(api):
    """Client authentifié en coach : utilisé par défaut dans les tests."""
    return TestClient(api, headers={"Authorization": f"Bearer {TOKEN_COACH}"})


@pytest.fixture()
def client_adherent(api):
    return TestClient(api, headers={"Authorization": f"Bearer {TOKEN_ADHERENT}"})


@pytest.fixture()
def client_sans_token(api):
    return TestClient(api)
