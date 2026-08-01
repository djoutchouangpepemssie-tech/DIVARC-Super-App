"""Couche 5 — Découverte : fil classé explicable, « voir moins », suggestions, recherche."""


def _post(client, H, body, visibility="public"):
    return client.post("/api/net/posts", headers=H, json={"body": body, "visibility": visibility}).json()["id"]


def _befriend(client, Ha, ua, Hb, ub):
    client.post(f"/api/net/friends/request/{ub['id']}", headers=Ha)
    client.post(f"/api/net/friends/accept/{ua['id']}", headers=Hb)


def test_fil_classe_expose_une_raison(client, auth):
    Ha, ua = auth("rk-a@divarc.fr")
    Hb, ub = auth("rk-b@divarc.fr")
    _befriend(client, Ha, ua, Hb, ub)
    _post(client, Hb, "post d'un ami")
    _post(client, Ha, "mon post")
    items = client.get("/api/net/feed?mode=ranked", headers=Ha).json()["items"]
    assert all("reason" in p for p in items)  # « Pourquoi je vois ça » sur chaque post
    reasons = {p["body"]: p["reason"] for p in items}
    assert reasons["post d'un ami"] == "Un ami proche a publié"
    assert reasons["mon post"] == "Ta publication"


def test_bascule_chronologique_permanente(client, auth):
    H, _ = auth("rk-chrono@divarc.fr")
    _post(client, H, "a")
    r = client.get("/api/net/feed?mode=recent", headers=H).json()
    assert r["mode"] == "recent" and r["items"][0]["reason"] == "Ordre chronologique"


def test_voir_moins_masque_le_post(client, auth):
    Ha, ua = auth("hide-a@divarc.fr")
    Hb, ub = auth("hide-b@divarc.fr")
    _befriend(client, Ha, ua, Hb, ub)
    pid = _post(client, Hb, "à cacher")
    assert "à cacher" in [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]
    client.post(f"/api/net/posts/{pid}/hide", headers=Ha)
    assert "à cacher" not in [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]


def test_suggestions_amis_en_commun(client, auth):
    Ha, ua = auth("sg-a@divarc.fr")
    Hb, ub = auth("sg-b@divarc.fr")
    Hc, uc = auth("sg-c@divarc.fr")
    _befriend(client, Ha, ua, Hb, ub)   # A-B amis
    _befriend(client, Hb, ub, Hc, uc)   # B-C amis
    sugg = client.get("/api/net/suggestions", headers=Ha).json()["items"]
    c = next((x for x in sugg if x["id"] == uc["id"]), None)
    assert c and c["mutual"] == 1 and "commun" in c["reason"]


def test_recherche_posts_et_personnes(client, auth):
    Ha, ua = auth("srch-licorne@divarc.fr")
    Hb, _ = auth("srch-viewer@divarc.fr")
    _post(client, Ha, "une licorne magique dans le pré", "public")
    res = client.get("/api/net/search?q=licorne", headers=Hb).json()
    assert any("licorne" in p["body"] for p in res["posts"])
    # recherche de personne par nom (dérivé de l'e-mail : « Srch-licorne »)
    ppl = client.get("/api/net/search?q=licorne", headers=Hb).json()["people"]
    assert any(u["id"] == ua["id"] for u in ppl)
