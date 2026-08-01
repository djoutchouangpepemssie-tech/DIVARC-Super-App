"""Phase 2 Éclats : cashback sur achat marketplace + boosts (puits) payés en Éclats."""


def test_cashback_sur_achat_marketplace(client, auth):
    # Un vendeur publie une annonce abordable
    Hs, _ = auth("seller-cb@divarc.fr")
    lid = client.post("/api/market/listings", headers=Hs, json={
        "title": "Casque audio", "description": "x", "priceCents": 5000, "category": "multimedia",
        "subcategory": "Informatique", "transactionType": "sale", "condition": "Bon état", "city": "Paris"}).json()["id"]
    # L'acheteur (solde démo suffisant) achète -> cashback 2% en Éclats
    Hb, ub = auth("buyer-cb@divarc.fr")
    before = client.get("/api/eclats", headers=Hb).json()["balance"]
    r = client.post(f"/api/market/listings/{lid}/buy", headers=Hb, json={}).json()
    assert r["ok"]
    expected = (5000 * 200) // 10000  # 100 Éclats
    assert r["eclatsCashback"] == expected
    assert client.get("/api/eclats", headers=Hb).json()["balance"] == before + expected


def test_boost_annonce_debite_des_eclats_et_remonte(client, auth):
    H, u = auth("seller-boost@divarc.fr")
    # crée une annonce à moi
    lid = client.post("/api/market/listings", headers=H, json={
        "title": "Mon vélo", "description": "bon état", "priceCents": 5000,
        "category": "loisirs", "subcategory": "Vélos", "transactionType": "sale",
        "condition": "Bon état", "city": "Paris"}).json()["id"]
    before = client.get("/api/eclats", headers=H).json()["balance"]
    r = client.post(f"/api/market/listings/{lid}/boost", headers=H).json()
    assert r["ok"] and r["cost"] == 50
    assert client.get("/api/eclats", headers=H).json()["balance"] == before - 50
    # l'annonce boostée remonte en tête du fil
    items = client.get("/api/market/listings", headers=H).json()
    assert items[0]["id"] == lid


def test_boost_annonce_reserve_au_vendeur(client, auth):
    Ha, _ = auth("owner@divarc.fr")
    Hb, _ = auth("intrus@divarc.fr")
    lid = client.post("/api/market/listings", headers=Ha, json={
        "title": "Table", "description": "x", "priceCents": 2000, "category": "maison",
        "subcategory": "Ameublement", "transactionType": "sale", "condition": "Bon état", "city": "Lyon"}).json()["id"]
    assert client.post(f"/api/market/listings/{lid}/boost", headers=Hb).status_code == 403


def test_boost_refuse_si_pas_assez_d_eclats(client, auth):
    H, _ = auth("fauche@divarc.fr")
    lid = client.post("/api/market/listings", headers=H, json={
        "title": "Lampe", "description": "x", "priceCents": 1000, "category": "maison",
        "subcategory": "Ameublement", "transactionType": "sale", "condition": "Bon état", "city": "Lille"}).json()["id"]
    # dépense tous les Éclats de bienvenue (100) via un cadeau
    Hb, ub = auth("ami-lampe@divarc.fr")
    client.post("/api/eclats/gift", headers=H, json={"toId": ub["id"], "amount": 100})
    assert client.post(f"/api/market/listings/{lid}/boost", headers=H).status_code == 402
