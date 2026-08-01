"""DIVARC+ : essai gratuit, avantages (likes illimités, révélation gratuite, cashback ×2, sans pub), abonnement."""
import app.config as configmod


def _profile(client, H, gender, seeking):
    return client.post("/api/dating/profile", headers=H, json={
        "birthDate": "1995-05-05", "gender": gender, "seeking": seeking, "city": "Paris", "lat": 48.85, "lon": 2.35})


def test_essai_gratuit_active_et_offre_des_eclats(client, auth):
    H, _ = auth("plus1@divarc.fr")
    assert client.get("/api/plus", headers=H).json()["active"] is False
    before = client.get("/api/eclats", headers=H).json()["balance"]
    r = client.post("/api/plus/trial", headers=H).json()
    assert r["active"] is True and r["trialUsed"] is True
    assert client.get("/api/eclats", headers=H).json()["balance"] == before + 200  # PLUS_MONTHLY_ECLATS
    # essai non rejouable
    assert client.post("/api/plus/trial", headers=H).status_code == 409


def test_plus_likes_illimites(client, auth, monkeypatch):
    # plafond très bas pour tester vite
    monkeypatch.setattr(configmod.settings, "DATING_DAILY_LIKES", 1)
    H, _ = auth("plus-like@divarc.fr")
    _profile(client, H, "homme", ["femme"])
    # cibles bidons (profils) pour liker
    targets = []
    for i in range(3):
        Ht, ut = auth(f"tgt{i}@divarc.fr")
        _profile(client, Ht, "femme", ["homme"])
        targets.append(ut["id"])
    # sans DIVARC+ : 2e like bloqué (plafond 1)
    assert client.post(f"/api/dating/swipe/{targets[0]}", headers=H, json={"action": "like"}).json()["match"] is False
    assert client.post(f"/api/dating/swipe/{targets[1]}", headers=H, json={"action": "like"}).status_code == 429
    # avec DIVARC+ : plus de limite
    client.post("/api/plus/trial", headers=H)
    assert client.post(f"/api/dating/swipe/{targets[1]}", headers=H, json={"action": "like"}).status_code == 200
    assert client.post(f"/api/dating/swipe/{targets[2]}", headers=H, json={"action": "like"}).status_code == 200


def test_plus_revelation_gratuite(client, auth):
    Ha, ua = auth("rev-plus@divarc.fr")
    Hb, ub = auth("rev-liker@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])
    client.post(f"/api/dating/swipe/{ua['id']}", headers=Hb, json={"action": "like"})
    client.post("/api/plus/trial", headers=Ha)
    bal = client.get("/api/eclats", headers=Ha).json()["balance"]
    r = client.post("/api/dating/likes/reveal", headers=Ha).json()
    assert any(x["userId"] == ub["id"] for x in r["revealed"])
    # gratuit : le solde d'Éclats ne bouge pas
    assert client.get("/api/eclats", headers=Ha).json()["balance"] == bal


def test_plus_cashback_double(client, auth):
    Hs, _ = auth("cb-seller@divarc.fr")
    lid = client.post("/api/market/listings", headers=Hs, json={
        "title": "Objet", "description": "x", "priceCents": 5000, "category": "maison",
        "subcategory": "Ameublement", "transactionType": "sale", "condition": "Bon état", "city": "Paris"}).json()["id"]
    Hb, _ = auth("cb-plus@divarc.fr")
    client.post("/api/plus/trial", headers=Hb)
    r = client.post(f"/api/market/listings/{lid}/buy", headers=Hb, json={}).json()
    # cashback ×2 : 2% * 2 = 4% de 5000 = 200 Éclats
    assert r["eclatsCashback"] == (5000 * 200 * 2) // 10000


def test_abonnement_debite_le_wallet_et_active(client, auth):
    H, _ = auth("sub@divarc.fr")  # DEMO_MODE -> wallet à 4800€
    before = client.get("/api/wallet", headers=H).json()["balanceCents"]
    r = client.post("/api/plus/subscribe", headers=H).json()
    assert r["active"] is True
    assert client.get("/api/wallet", headers=H).json()["balanceCents"] == before - 999  # PLUS_PRICE_CENTS
