"""Arcade : partie gratuite/jour puis entrée payante, récompense DÉTERMINISTE par score, classement."""
import app.config as configmod


def test_partie_gratuite_puis_payante_et_recompense_par_score(client, auth):
    H, _ = auth("arcade1@divarc.fr")
    start = client.get("/api/eclats", headers=H).json()["balance"]  # 100 (bienvenue)

    # 1re partie du jour = gratuite
    p1 = client.post("/api/arcade/reflex/play", headers=H).json()
    assert p1["free"] is True and p1["cost"] == 0
    # score élevé -> palier 20 Éclats (déterministe)
    r1 = client.post("/api/arcade/reflex/score", headers=H, json={"sessionId": p1["sessionId"], "score": 25}).json()
    assert r1["reward"] == 20 and r1["myBest"] == 25
    assert client.get("/api/eclats", headers=H).json()["balance"] == start + 20

    # 2e partie = payante (5 Éclats)
    bal = client.get("/api/eclats", headers=H).json()["balance"]
    p2 = client.post("/api/arcade/reflex/play", headers=H).json()
    assert p2["free"] is False and p2["cost"] == 5
    assert client.get("/api/eclats", headers=H).json()["balance"] == bal - 5


def test_score_deterministe_selon_paliers(client, auth):
    H, _ = auth("arcade2@divarc.fr")
    # score faible -> 0 récompense
    p = client.post("/api/arcade/reflex/play", headers=H).json()
    r = client.post("/api/arcade/reflex/score", headers=H, json={"sessionId": p["sessionId"], "score": 3}).json()
    assert r["reward"] == 0


def test_score_borne_et_pas_de_double(client, auth):
    H, _ = auth("arcade3@divarc.fr")
    p = client.post("/api/arcade/reflex/play", headers=H).json()
    # score aberrant -> borné à maxScore (60) -> palier max 20
    r = client.post("/api/arcade/reflex/score", headers=H, json={"sessionId": p["sessionId"], "score": 99999}).json()
    assert r["score"] == 60 and r["reward"] == 20
    # rejouer le même score = refusé
    assert client.post("/api/arcade/reflex/score", headers=H, json={"sessionId": p["sessionId"], "score": 60}).status_code == 409


def test_entree_refusee_si_pas_assez_d_eclats(client, auth, monkeypatch):
    monkeypatch.setattr(configmod.settings, "ARCADE_FREE_DAILY", 0)  # plus de partie gratuite
    monkeypatch.setattr(configmod.settings, "ARCADE_ENTRY", 100)
    H, ub = auth("arcade4@divarc.fr")
    # vider les Éclats via un cadeau
    Hx, ux = auth("arcade4b@divarc.fr")
    client.post("/api/eclats/gift", headers=H, json={"toId": ux["id"], "amount": 100})
    assert client.post("/api/arcade/reflex/play", headers=H).status_code == 402


def test_classement_hebdo(client, auth):
    Ha, ua = auth("lb-a@divarc.fr")
    Hb, ub = auth("lb-b@divarc.fr")
    pa = client.post("/api/arcade/reflex/play", headers=Ha).json()
    client.post("/api/arcade/reflex/score", headers=Ha, json={"sessionId": pa["sessionId"], "score": 30})
    pb = client.post("/api/arcade/reflex/play", headers=Hb).json()
    client.post("/api/arcade/reflex/score", headers=Hb, json={"sessionId": pb["sessionId"], "score": 10})
    lb = client.get("/api/arcade/reflex/leaderboard", headers=Ha).json()["leaderboard"]
    assert lb[0]["userId"] == ua["id"] and lb[0]["rank"] == 1  # meilleur score en tête
