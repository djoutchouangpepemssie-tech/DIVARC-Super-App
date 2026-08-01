"""Couche 3 — Interagir : réactions, commentaires imbriqués, partages, bookmarks."""


def _post(client, H, body="hello", visibility="public"):
    return client.post("/api/net/posts", headers=H, json={"body": body, "visibility": visibility}).json()["id"]


def test_reactions_une_par_user_et_changement(client, auth):
    Ha, _ = auth("rx-a@divarc.fr")
    Hb, _ = auth("rx-b@divarc.fr")
    pid = _post(client, Ha)
    r = client.put(f"/api/net/posts/{pid}/reactions", headers=Hb, json={"type": "love"}).json()
    assert r["total"] == 1 and r["myReaction"] == "love"
    # changer de type ne double pas
    r = client.put(f"/api/net/posts/{pid}/reactions", headers=Hb, json={"type": "bravo"}).json()
    assert r["total"] == 1
    # visible dans le feed de l'auteur
    feed = client.get("/api/net/feed", headers=Ha).json()["items"]
    p = next(x for x in feed if x["id"] == pid)
    assert p["reactions"]["total"] == 1 and p["reactions"]["byType"]["bravo"] == 1
    # retrait
    assert client.delete(f"/api/net/posts/{pid}/reactions", headers=Hb).json()["total"] == 0


def test_reaction_type_invalide_refuse(client, auth):
    H, _ = auth("rx-bad@divarc.fr")
    pid = _post(client, H)
    assert client.put(f"/api/net/posts/{pid}/reactions", headers=H, json={"type": "nope"}).status_code == 400


def test_commentaires_imbriques(client, auth):
    Ha, _ = auth("cm-a@divarc.fr")
    Hb, ub = auth("cm-b@divarc.fr")
    pid = _post(client, Ha)
    c1 = client.post(f"/api/net/posts/{pid}/comments", headers=Hb, json={"body": "top-level"}).json()
    assert c1["depth"] == 0 and c1["parentId"] is None
    c2 = client.post(f"/api/net/posts/{pid}/comments", headers=Ha, json={"body": "réponse", "parentId": c1["id"]}).json()
    assert c2["depth"] == 1 and c2["parentId"] == c1["id"]
    items = client.get(f"/api/net/posts/{pid}/comments", headers=Ha).json()["items"]
    assert len(items) == 2
    # compteur de commentaires sur le post
    feed = client.get("/api/net/feed", headers=Ha).json()["items"]
    assert next(x for x in feed if x["id"] == pid)["commentCount"] == 2


def test_supprimer_commentaire_auteur_ou_auteur_du_post(client, auth):
    Ha, _ = auth("del-post-owner@divarc.fr")
    Hb, _ = auth("del-commenter@divarc.fr")
    Hc, _ = auth("del-outsider@divarc.fr")
    pid = _post(client, Ha)
    c = client.post(f"/api/net/posts/{pid}/comments", headers=Hb, json={"body": "à modérer"}).json()
    # un tiers ne peut pas
    assert client.delete(f"/api/net/comments/{c['id']}", headers=Hc).status_code == 403
    # l'auteur du post peut modérer (supprimer) le commentaire
    assert client.delete(f"/api/net/comments/{c['id']}", headers=Ha).json()["ok"] is True
    items = client.get(f"/api/net/posts/{pid}/comments", headers=Ha).json()["items"]
    assert items[0]["deleted"] is True and items[0]["body"] == ""


def test_partage_uniquement_du_public(client, auth):
    Ha, _ = auth("sh-a@divarc.fr")
    Hb, _ = auth("sh-b@divarc.fr")
    pub = _post(client, Ha, "public post", "public")
    priv = _post(client, Ha, "privé", "only_me")
    shared = client.post(f"/api/net/posts/{pub}/share", headers=Hb, json={"body": "regardez !"}).json()
    assert shared["type"] == "share" and shared["sharedPost"]["id"] == pub
    # un post non-public n'est pas partageable (invisible -> 404)
    assert client.post(f"/api/net/posts/{priv}/share", headers=Hb, json={}).status_code == 404


def test_bookmarks_toggle_et_liste(client, auth):
    Ha, _ = auth("bk-a@divarc.fr")
    Hb, _ = auth("bk-b@divarc.fr")
    pid = _post(client, Ha)
    assert client.put(f"/api/net/posts/{pid}/bookmark", headers=Hb).json()["bookmarked"] is True
    ids = [p["id"] for p in client.get("/api/net/bookmarks", headers=Hb).json()["items"]]
    assert pid in ids
    # re-toggle retire
    assert client.put(f"/api/net/posts/{pid}/bookmark", headers=Hb).json()["bookmarked"] is False
    assert client.get("/api/net/bookmarks", headers=Hb).json()["items"] == []
