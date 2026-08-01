"""Tests du parcours critique DIVARC (auth, wallet, messagerie, social, marketplace, ads)."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "live"


def test_auth_401_sans_token(client):
    r = client.get("/api/wallet")
    assert r.status_code == 401
    assert r.json() == {"error": "Non authentifié"}


def test_otp_flow_et_provisioning(client):
    # OTP send -> code preview
    r = client.post("/api/auth/otp/send", json={"email": "alice@divarc.fr"})
    assert r.status_code == 200
    code = r.json()["previewCode"]
    assert code and len(code) == 6

    # Mauvais code -> refusé
    assert client.post("/api/auth/otp/verify", json={"email": "alice@divarc.fr", "code": "000000"}).status_code == 400

    # Bon code -> token + nouvel utilisateur
    r = client.post("/api/auth/otp/verify", json={"email": "alice@divarc.fr", "code": code})
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["isNew"] is True

    # Wallet provisionné à 480000c + 2 coffres
    H = {"Authorization": f"Bearer {body['token']}"}
    w = client.get("/api/wallet", headers=H).json()
    assert w["balanceCents"] == 480000
    assert len(w["coffres"]) == 2


def test_send_p2p_idempotence(client, auth):
    H, _ = auth()
    r1 = client.post("/api/send", headers=H, json={"toName": "Marie", "amountCents": 2000, "idempotencyKey": "k1"})
    assert r1.status_code == 200
    assert r1.json()["balanceCents"] == 478000
    # Rejouer la même clé -> pas de re-débit
    r2 = client.post("/api/send", headers=H, json={"toName": "Marie", "amountCents": 2000, "idempotencyKey": "k1"})
    assert r2.json().get("idempotent") is True
    assert client.get("/api/wallet", headers=H).json()["balanceCents"] == 478000


def test_send_solde_insuffisant(client, auth):
    H, _ = auth()
    r = client.post("/api/send", headers=H, json={"toName": "Marie", "amountCents": 99999999})
    assert r.status_code == 402


def test_enveloppe_somme_egale_total(client, auth):
    H, _ = auth()
    for count in (1, 3, 5, 8):
        r = client.post("/api/enveloppe/create", headers=H, json={"totalCents": 3333, "count": count})
        shares = r.json()["enveloppe"]["shares"]
        assert len(shares) == count
        assert sum(s["amountCents"] for s in shares) == 3333


def test_conversation_bienvenue_officielle(client, auth):
    H, _ = auth()
    convos = client.get("/api/conversations", headers=H).json()
    # DM de bienvenue du compte OFFICIEL DIVARC (pas d'un ami)
    assert any(c.get("title") == "DIVARC" for c in convos)


def test_messagerie_xp_et_bot_reply(client, auth):
    H, _ = auth()
    client.get("/api/conversations", headers=H)  # provisionne les bots démo
    # DM avec un bot démo (Marie) -> réponse automatique
    conv = client.post("/api/conversations", headers=H, json={"type": "dm", "memberHandles": ["@marie"]}).json()
    cid = conv["id"]
    r = client.post(f"/api/conversations/{cid}/messages", headers=H, json={"text": "Salut !"})
    # +10 (moi) puis +10 (réponse du bot) = 20
    assert r.json()["friendship"]["xp"] == 20


def test_social_feed_et_seed(client, auth):
    H, _ = auth()
    feed = client.get("/api/social/feed", headers=H).json()
    assert len(feed) >= 8
    assert all("author" in p for p in feed if not p.get("sponsored"))


def test_marketplace_seed_et_filtres(client, auth):
    H, _ = auth()
    items = client.get("/api/market/listings", headers=H).json()
    assert len(items) == 12
    voitures = client.get("/api/market/listings?cat=vehicules", headers=H).json()
    assert all(i["category"] == "vehicules" for i in voitures)


def test_marketplace_achat_flux_argent(client, auth):
    Hb, _ = auth("buyer@divarc.fr")
    items = client.get("/api/market/listings", headers=Hb).json()
    # une annonce d'un bot, pas la sienne, active
    target = next(i for i in items if i["priceCents"] <= 480000 and i["status"] == "active")
    r = client.post(f"/api/market/listings/{target['id']}/buy", headers=Hb)
    assert r.status_code == 200
    assert r.json()["balanceCents"] == 480000 - target["priceCents"]
    # racheter -> déjà vendu
    assert client.post(f"/api/market/listings/{target['id']}/buy", headers=Hb).status_code == 410


def test_store_apps_37_et_connect(client, auth):
    H, _ = auth()
    apps = client.get("/api/store/apps", headers=H).json()
    assert len(apps) == 37
    # les apps "featured" apparaissent d'abord
    assert apps[0]["featured"] is True
    r = client.post("/api/store/apps/spotify/connect", headers=H).json()
    assert r["connection"]["pseudonym"].startswith("divarc-")
    # idempotent : même pseudonyme
    r2 = client.post("/api/store/apps/spotify/connect", headers=H).json()
    assert r2["existing"] is True
    assert r2["connection"]["pseudonym"] == r["connection"]["pseudonym"]


def test_ads_creation_et_debit(client, auth):
    H, _ = auth()
    r = client.post("/api/ads/campaigns", headers=H, json={"name": "Test", "type": "display", "budgetCents": 30000})
    assert r.status_code == 200
    assert r.json()["balanceCents"] == 480000 - 30000
    assert r.json()["campaign"]["status"] == "active"


def test_admin_connectors_et_isolation(client, auth):
    Ha, _ = auth("ha@divarc.fr")
    Hb, _ = auth("hb@divarc.fr")
    conns = client.get("/api/admin/connectors", headers=Ha).json()
    assert len(conns) == 5
    client.post("/api/admin/connectors/impots/connect", headers=Ha)
    # isolation : hb ne voit pas la connexion de ha
    conns_b = client.get("/api/admin/connectors", headers=Hb).json()
    assert next(c for c in conns_b if c["id"] == "impots")["connected"] is False


def test_ai_sans_cle_renvoie_503(client, auth):
    H, _ = auth()
    r = client.post("/api/ai/chat", headers=H, json={"text": "Envoie 20 euros a Marie"})
    assert r.status_code == 503
