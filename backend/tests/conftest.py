"""Fixtures de test : client HTTP FastAPI branché sur une MongoDB en mémoire."""
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import app.db as dbmod
import app.main as mainmod


@pytest.fixture
def client(monkeypatch):
    # Base MongoDB en mémoire, neuve pour chaque test
    dbmod._db = AsyncMongoMockClient(tz_aware=True)["divarc_test"]

    async def fake_connect():
        return dbmod._db

    # Patch dans les deux modules (db + main capture la référence à l'import)
    monkeypatch.setattr(dbmod, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(mainmod, "connect_to_mongo", fake_connect)

    with TestClient(mainmod.app) as c:
        yield c


@pytest.fixture
def auth(client):
    """Retourne (headers, user) d'un utilisateur fraîchement provisionné."""
    def _make(email="tester@divarc.fr"):
        code = client.post("/api/auth/otp/send", json={"email": email}).json()["previewCode"]
        r = client.post("/api/auth/otp/verify", json={"email": email, "code": code}).json()
        return {"Authorization": f"Bearer {r['token']}"}, r["user"]
    return _make
