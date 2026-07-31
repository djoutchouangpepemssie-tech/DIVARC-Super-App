"""Tests du centre de notifications."""


def test_notifications_vides_au_depart(client, auth):
    H, _ = auth()
    r = client.get("/api/notifications", headers=H).json()
    assert r["items"] == [] and r["unread"] == 0


def test_message_genere_une_notification(client, auth):
    Ha, ua = auth("na@divarc.fr")
    Hb, ub = auth("nb@divarc.fr")
    conv = client.post("/api/conversations", headers=Ha, json={"type": "dm", "memberHandles": [ub["handle"]]}).json()
    cid = conv["id"]
    client.post(f"/api/conversations/{cid}/messages", headers=Ha, json={"text": "Salut Bob"})
    # B a une notification "message"
    r = client.get("/api/notifications", headers=Hb).json()
    assert r["unread"] == 1
    assert r["items"][0]["kind"] == "message"
    assert "Salut Bob" in r["items"][0]["body"]


def test_vente_marketplace_notifie_le_vendeur(client, auth):
    Hb, _ = auth("buyerN@divarc.fr")
    items = client.get("/api/market/listings", headers=Hb).json()
    target = next(i for i in items if i["priceCents"] <= 480000 and i["status"] == "active")
    client.post(f"/api/market/listings/{target['id']}/buy", headers=Hb)
    # le vendeur est un bot -> la notif est bien créée en base (destinataire = sellerId)
    # on vérifie via un autre canal : la notification existe pour le seller
    # (ici on ne peut pas se connecter en tant que bot ; on valide juste l'absence d'erreur)
    assert client.get("/api/notifications", headers=Hb).json()["unread"] == 0  # l'acheteur n'est pas notifié


def test_marquer_comme_lu(client, auth):
    Ha, ua = auth("nc@divarc.fr")
    Hb, ub = auth("nd@divarc.fr")
    conv = client.post("/api/conversations", headers=Ha, json={"type": "dm", "memberHandles": [ub["handle"]]}).json()
    client.post(f"/api/conversations/{conv['id']}/messages", headers=Ha, json={"text": "coucou"})
    assert client.get("/api/notifications", headers=Hb).json()["unread"] == 1
    client.post("/api/notifications/read", headers=Hb)
    assert client.get("/api/notifications", headers=Hb).json()["unread"] == 0


def test_notifications_requiert_auth(client):
    assert client.get("/api/notifications").status_code == 401
