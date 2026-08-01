"""Fixtures de test : client FastAPI (Mongo en mémoire + base social SQLite isolée)."""
import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import app.config as configmod
import app.db as dbmod
import app.main as mainmod
import app.social.adapters.persistence.db as socialdb


@pytest.fixture
def client(monkeypatch, tmp_path):
    # La plupart des tests s'appuient sur les données de démo (solde, annonces, bots)
    monkeypatch.setattr(configmod.settings, "DEMO_MODE", True)
    # Contexte social : base SQLite fichier, isolée par test. Le schéma est créé par le
    # lifespan de l'app (create_all), sur la bonne boucle d'événements.
    dbfile = tmp_path / "social.db"
    monkeypatch.setattr(configmod.settings, "SOCIAL_DATABASE_URL",
                        f"sqlite+aiosqlite:///{dbfile.as_posix()}")
    socialdb._engine = None
    socialdb._sessionmaker = None

    # Base MongoDB en mémoire, neuve pour chaque test
    dbmod._db = AsyncMongoMockClient(tz_aware=True)["divarc_test"]

    async def fake_connect():
        return dbmod._db

    # Patch dans les deux modules (db + main capture la référence à l'import)
    monkeypatch.setattr(dbmod, "connect_to_mongo", fake_connect)
    monkeypatch.setattr(mainmod, "connect_to_mongo", fake_connect)

    with TestClient(mainmod.app) as c:
        yield c

    socialdb._engine = None
    socialdb._sessionmaker = None


@pytest.fixture
def auth(client):
    """Retourne (headers, user) d'un utilisateur fraîchement provisionné."""
    def _make(email="tester@divarc.fr"):
        code = client.post("/api/auth/otp/send", json={"email": email}).json()["previewCode"]
        r = client.post("/api/auth/otp/verify", json={"email": email, "code": code}).json()
        return {"Authorization": f"Bearer {r['token']}"}, r["user"]
    return _make
