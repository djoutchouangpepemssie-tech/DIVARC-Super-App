"""Économie Éclats : bienvenue, check-in/série, cadeau, idempotence, sens unique."""


def test_cadeau_de_bienvenue(client, auth):
    H, _ = auth("ec1@divarc.fr")
    r = client.get("/api/eclats", headers=H).json()
    assert r["balance"] == 100  # ECLATS_WELCOME
    assert "valeur monétaire" in r["disclaimer"].lower()


def test_checkin_credite_et_bloque_deux_fois(client, auth):
    H, _ = auth("ec2@divarc.fr")
    before = client.get("/api/eclats", headers=H).json()["balance"]
    r = client.post("/api/eclats/checkin", headers=H).json()
    assert r["ok"] and r["streak"] == 1
    assert client.get("/api/eclats", headers=H).json()["balance"] == before + r["reward"]
    # 2e check-in le même jour -> refusé
    assert client.post("/api/eclats/checkin", headers=H).status_code == 409


def test_cadeau_a_un_contact(client, auth):
    Ha, ua = auth("giver@divarc.fr")
    Hb, ub = auth("receiver@divarc.fr")
    client.patch("/api/users/me", headers=Hb, json={"handle": "receiver1"})
    r = client.post("/api/eclats/gift", headers=Ha, json={"toHandle": "@receiver1", "amount": 30}).json()
    assert r["ok"] and r["balance"] == 70  # 100 - 30
    assert client.get("/api/eclats", headers=Hb).json()["balance"] == 130  # 100 + 30


def test_cadeau_refuse_si_solde_insuffisant(client, auth):
    Ha, _ = auth("poor@divarc.fr")
    Hb, ub = auth("rich@divarc.fr")
    r = client.post("/api/eclats/gift", headers=Ha, json={"toId": ub["id"], "amount": 999})
    assert r.status_code == 400
    assert client.get("/api/eclats", headers=Ha).json()["balance"] == 100  # inchangé


def test_pas_de_cadeau_a_soi_meme(client, auth):
    H, u = auth("selfgift@divarc.fr")
    assert client.post("/api/eclats/gift", headers=H, json={"toId": u["id"], "amount": 10}).status_code == 400


def test_parrainage_credite_des_eclats(client, auth):
    Ha, _ = auth("parrain@divarc.fr")
    inv = client.post("/api/discover/invite", headers=Ha).json()
    before = client.get("/api/eclats", headers=Ha).json()["balance"]
    code = client.post("/api/auth/otp/send", json={"email": "filleul@divarc.fr"}).json()["previewCode"]
    client.post("/api/auth/otp/verify", json={"email": "filleul@divarc.fr", "code": code, "invite": inv["code"]})
    after = client.get("/api/eclats", headers=Ha).json()["balance"]
    assert after == before + 50  # ECLATS_REFERRAL pour le parrain
