"""Couche 4 — Graphe social : amis, suivi, blocage/sourdine, cercles, profil."""


def _post(client, H, body, visibility="public", audience=None):
    payload = {"body": body, "visibility": visibility}
    if audience:
        payload["audience"] = audience
    return client.post("/api/net/posts", headers=H, json=payload).json()["id"]


def test_amitie_demande_puis_acceptation(client, auth):
    Ha, ua = auth("fr-a@divarc.fr")
    Hb, ub = auth("fr-b@divarc.fr")
    assert client.post(f"/api/net/friends/request/{ub['id']}", headers=Ha).json()["status"] == "pending"
    # B voit la demande entrante
    reqs = client.get("/api/net/friends/requests", headers=Hb).json()
    assert any(x["id"] == ua["id"] for x in reqs["incoming"])
    # B accepte -> amis mutuels
    assert client.post(f"/api/net/friends/accept/{ua['id']}", headers=Hb).json()["status"] == "friends"
    assert client.get("/api/net/relationship/" + ub["id"], headers=Ha).json()["friend"] is True
    assert any(x["id"] == ub["id"] for x in client.get("/api/net/friends", headers=Ha).json()["items"])


def test_demande_mutuelle_devient_amitie(client, auth):
    Ha, ua = auth("mu-a@divarc.fr")
    Hb, ub = auth("mu-b@divarc.fr")
    client.post(f"/api/net/friends/request/{ub['id']}", headers=Ha)
    # B demande aussi -> amitié directe
    assert client.post(f"/api/net/friends/request/{ua['id']}", headers=Hb).json()["status"] == "friends"


def test_suivi_et_desabonnement(client, auth):
    Ha, ua = auth("fo-a@divarc.fr")
    Hb, ub = auth("fo-b@divarc.fr")
    assert client.post(f"/api/net/follow/{ub['id']}", headers=Ha).json()["following"] is True
    assert client.get(f"/api/net/relationship/{ub['id']}", headers=Ha).json()["following"] is True
    assert client.delete(f"/api/net/follow/{ub['id']}", headers=Ha).json()["following"] is False


def test_blocage_rompt_l_amitie_et_masque_le_feed(client, auth):
    Ha, ua = auth("bl-a@divarc.fr")
    Hb, ub = auth("bl-b@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    _post(client, Hb, "coucou")
    assert "coucou" in [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]
    # A bloque B -> le post de B disparaît du feed de A
    client.post(f"/api/net/block/{ub['id']}", headers=Ha)
    assert "coucou" not in [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]


def test_sourdine_masque_le_feed_sans_bloquer(client, auth):
    Ha, _ = auth("mt-a@divarc.fr")
    Hb, ub = auth("mt-b@divarc.fr")
    Hc, uc = auth("mt-c@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    client.post(f"/api/net/follow/{uc['id']}", headers=Ha)
    _post(client, Hb, "de B")
    _post(client, Hc, "de C")
    client.post(f"/api/net/mute/{uc['id']}", headers=Ha)
    bodies = [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]
    assert "de B" in bodies and "de C" not in bodies


def test_cercles_visibilite(client, auth):
    Ha, ua = auth("ci-a@divarc.fr")
    Hb, ub = auth("ci-b@divarc.fr")   # dans le cercle
    Hc, uc = auth("ci-c@divarc.fr")   # hors cercle
    cid = client.post("/api/net/circles", headers=Ha, json={"name": "Proches"}).json()["id"]
    client.put(f"/api/net/circles/{cid}/members/{ub['id']}", headers=Ha)
    pid = _post(client, Ha, "cercle only", visibility="circles", audience={"circle_ids": [cid]})
    assert client.get(f"/api/net/posts/{pid}", headers=Hb).status_code == 200   # membre voit
    assert client.get(f"/api/net/posts/{pid}", headers=Hc).status_code == 404   # non-membre ne voit pas


def test_profil_mise_a_jour_et_public(client, auth):
    Ha, ua = auth("pr-a@divarc.fr")
    Hb, ub = auth("pr-b@divarc.fr")
    r = client.put("/api/net/profile", headers=Ha, json={"displayName": "Alice Réseau", "bio": "Bonjour", "handle": "alice_net"}).json()
    assert r["name"] == "Alice Réseau" and r["handle"] == "alice_net" and r["bio"] == "Bonjour"
    # profil public vu par B (avec relation)
    pub = client.get(f"/api/net/profile/{ua['id']}", headers=Hb).json()
    assert pub["name"] == "Alice Réseau" and pub["relationship"]["friend"] is False


def test_handle_unique(client, auth):
    Ha, _ = auth("h1@divarc.fr")
    Hb, _ = auth("h2@divarc.fr")
    client.put("/api/net/profile", headers=Ha, json={"handle": "pris"})
    assert client.put("/api/net/profile", headers=Hb, json={"handle": "pris"}).status_code == 409
