"""Couche 8 — Notifications sociales (persistées via le système existant) + préférences."""


def test_reaction_cree_une_notification(client, auth):
    Ha, ua = auth("no-a@divarc.fr")
    Hb, ub = auth("no-b@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "coucou"}).json()["id"]
    client.put(f"/api/net/posts/{pid}/reactions", headers=Hb, json={"type": "love"})
    # l'auteur du post reçoit une notification sociale
    notifs = client.get("/api/notifications", headers=Ha).json()
    assert notifs["unread"] >= 1
    n = notifs["items"][0]
    assert n["kind"] == "social" and n["meta"]["netKind"] == "reaction" and n["meta"]["postId"] == pid


def test_commentaire_et_reponse_notifient(client, auth):
    Ha, ua = auth("nc-a@divarc.fr")
    Hb, ub = auth("nc-b@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "post"}).json()["id"]
    c = client.post(f"/api/net/posts/{pid}/comments", headers=Hb, json={"body": "sympa"}).json()
    # A (auteur du post) notifié du commentaire
    assert any(n["meta"].get("netKind") == "comment" for n in client.get("/api/notifications", headers=Ha).json()["items"])
    # A répond -> B (auteur du commentaire) notifié
    client.post(f"/api/net/posts/{pid}/comments", headers=Ha, json={"body": "merci", "parentId": c["id"]})
    assert any(n["meta"].get("netKind") == "reply" for n in client.get("/api/notifications", headers=Hb).json()["items"])


def test_ami_accepte_notifie(client, auth):
    Ha, ua = auth("nf-a@divarc.fr")
    Hb, ub = auth("nf-b@divarc.fr")
    client.post(f"/api/net/friends/request/{ub['id']}", headers=Ha)
    client.post(f"/api/net/friends/accept/{ua['id']}", headers=Hb)
    assert any(n["meta"].get("netKind") == "friend_accept" for n in client.get("/api/notifications", headers=Ha).json()["items"])


def test_preferences_desactivent_une_notification(client, auth):
    Ha, ua = auth("np-a@divarc.fr")
    Hb, _ = auth("np-b@divarc.fr")
    # A désactive les notifications de réaction
    client.put("/api/net/notifications/prefs", headers=Ha, json={"disabled": ["reaction"]})
    assert "reaction" in client.get("/api/net/notifications/prefs", headers=Ha).json()["disabled"]
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "x"}).json()["id"]
    before = client.get("/api/notifications", headers=Ha).json()["unread"]
    client.put(f"/api/net/posts/{pid}/reactions", headers=Hb, json={"type": "like"})
    # aucune notification de réaction créée
    after = client.get("/api/notifications", headers=Ha).json()["unread"]
    assert after == before


def test_pas_d_auto_notification(client, auth):
    Ha, _ = auth("ns-a@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "moi"}).json()["id"]
    client.put(f"/api/net/posts/{pid}/reactions", headers=Ha, json={"type": "like"})  # je réagis à MON post
    assert client.get("/api/notifications", headers=Ha).json()["unread"] == 0
