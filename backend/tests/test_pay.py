"""Tests du paiement par QR."""


def test_qr_create_avec_montant(client, auth):
    H, _ = auth()
    r = client.post("/api/pay/qr/create", headers=H, json={"amountCents": 1500, "note": "Café"}).json()
    assert r["amountCents"] == 1500
    assert len(r["code"]) == 8
    assert r["qr"].startswith("data:image/svg+xml")  # data URI du QR


def test_qr_flux_paiement_complet(client, auth):
    Hp, up = auth("payee@divarc.fr")     # bénéficiaire
    Hb, ub = auth("payer@divarc.fr")     # payeur
    # le bénéficiaire crée une demande de 2000c
    code = client.post("/api/pay/qr/create", headers=Hp, json={"amountCents": 2000}).json()["code"]
    # le payeur voit les détails
    det = client.get(f"/api/pay/qr/{code}", headers=Hb).json()
    assert det["amountCents"] == 2000 and det["payee"]["id"] == up["id"] and det["isMine"] is False
    # le payeur paie
    r = client.post(f"/api/pay/qr/{code}/pay", headers=Hb).json()
    assert r["ok"] and r["balanceCents"] == 480000 - 2000
    # le bénéficiaire a bien été crédité
    assert client.get("/api/wallet", headers=Hp).json()["balanceCents"] == 480000 + 2000
    # notification côté bénéficiaire
    assert client.get("/api/notifications", headers=Hp).json()["unread"] == 1


def test_qr_deja_paye(client, auth):
    Hp, _ = auth("p2@divarc.fr")
    Hb, _ = auth("b2@divarc.fr")
    code = client.post("/api/pay/qr/create", headers=Hp, json={"amountCents": 1000}).json()["code"]
    client.post(f"/api/pay/qr/{code}/pay", headers=Hb)
    # re-payer -> refusé (409)
    assert client.post(f"/api/pay/qr/{code}/pay", headers=Hb).status_code == 409


def test_qr_montant_libre(client, auth):
    Hp, _ = auth("p3@divarc.fr")
    Hb, _ = auth("b3@divarc.fr")
    # demande sans montant -> le payeur choisit
    code = client.post("/api/pay/qr/create", headers=Hp, json={}).json()["code"]
    assert client.get(f"/api/pay/qr/{code}", headers=Hb).json()["amountCents"] is None
    r = client.post(f"/api/pay/qr/{code}/pay", headers=Hb, json={"amountCents": 3000}).json()
    assert r["amountCents"] == 3000


def test_qr_ne_peut_pas_se_payer_soi_meme(client, auth):
    Hp, _ = auth()
    code = client.post("/api/pay/qr/create", headers=Hp, json={"amountCents": 1000}).json()["code"]
    assert client.post(f"/api/pay/qr/{code}/pay", headers=Hp).status_code == 400


def test_qr_solde_insuffisant(client, auth):
    Hp, _ = auth("p4@divarc.fr")
    Hb, _ = auth("b4@divarc.fr")
    code = client.post("/api/pay/qr/create", headers=Hp, json={"amountCents": 99999999}).json()["code"]
    assert client.post(f"/api/pay/qr/{code}/pay", headers=Hb).status_code == 402


def test_qr_introuvable(client, auth):
    Hb, _ = auth()
    assert client.get("/api/pay/qr/ZZZZZZZZ", headers=Hb).status_code == 404
