"""DIVARC Rencontres : âge 18+, profils, swipe/match, super-like (Éclats), blocage, RGPD."""


def _profile(client, H, gender, seeking, birth="1995-05-05", lat=48.85, lon=2.35):
    return client.post("/api/dating/profile", headers=H, json={
        "birthDate": birth, "gender": gender, "seeking": seeking,
        "bio": "Salut", "city": "Paris", "lat": lat, "lon": lon,
    })


def test_mineur_refuse(client, auth):
    H, _ = auth("teen@divarc.fr")
    r = _profile(client, H, "homme", ["femme"], birth="2010-01-01")
    assert r.status_code == 403


def test_localisation_approximative(client, auth):
    H, _ = auth("geo@divarc.fr")
    p = _profile(client, H, "femme", ["homme"], lat=48.856614, lon=2.352222).json()
    # arrondi à 2 décimales -> jamais la position exacte
    assert p["lat"] == 48.86 and p["lon"] == 2.35


def test_swipe_reciproque_cree_un_match_et_une_conversation(client, auth):
    Ha, ua = auth("alice@divarc.fr")
    Hb, ub = auth("bob@divarc.fr")
    _profile(client, Ha, "femme", ["homme"])
    _profile(client, Hb, "homme", ["femme"])
    # A like B (pas encore de match)
    assert client.post(f"/api/dating/swipe/{ub['id']}", headers=Ha, json={"action": "like"}).json()["match"] is False
    # B like A -> match + conversation
    r = client.post(f"/api/dating/swipe/{ua['id']}", headers=Hb, json={"action": "like"}).json()
    assert r["match"] is True and r["conversationId"]
    # la conversation apparaît dans la messagerie des deux
    assert any(c["id"] == r["conversationId"] for c in client.get("/api/conversations", headers=Ha).json())
    assert any(c["id"] == r["conversationId"] for c in client.get("/api/conversations", headers=Hb).json())


def test_superlike_debite_des_eclats(client, auth):
    Ha, _ = auth("sl-a@divarc.fr")
    Hb, ub = auth("sl-b@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])
    before = client.get("/api/eclats", headers=Ha).json()["balance"]
    assert client.post(f"/api/dating/swipe/{ub['id']}", headers=Ha, json={"action": "superlike"}).json()["match"] is False
    assert client.get("/api/eclats", headers=Ha).json()["balance"] == before - 15  # ECLATS_SUPERLIKE


def test_decouverte_respecte_preferences_et_exclut_deja_swipe(client, auth):
    Ha, ua = auth("d-a@divarc.fr")
    Hb, ub = auth("d-b@divarc.fr")
    Hc, uc = auth("d-c@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])   # compatible avec A
    _profile(client, Hc, "homme", ["femme"])   # incompatible (A ne cherche pas homme)
    ids = [c["userId"] for c in client.get("/api/dating/discover", headers=Ha).json()]
    assert ub["id"] in ids and uc["id"] not in ids
    # après un swipe, B disparaît de la découverte
    client.post(f"/api/dating/swipe/{ub['id']}", headers=Ha, json={"action": "pass"})
    ids2 = [c["userId"] for c in client.get("/api/dating/discover", headers=Ha).json()]
    assert ub["id"] not in ids2


def test_blocage_exclut_de_la_decouverte(client, auth):
    Ha, ua = auth("b-a@divarc.fr")
    Hb, ub = auth("b-b@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])
    client.post(f"/api/discover/block/{ub['id']}", headers=Ha)
    ids = [c["userId"] for c in client.get("/api/dating/discover", headers=Ha).json()]
    assert ub["id"] not in ids


def test_reveal_qui_ta_like_paye_en_eclats(client, auth):
    Ha, ua = auth("r-a@divarc.fr")
    Hb, ub = auth("r-b@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])
    client.post(f"/api/dating/swipe/{ua['id']}", headers=Hb, json={"action": "like"})  # B like A
    assert client.get("/api/dating/likes", headers=Ha).json()["count"] == 1
    before = client.get("/api/eclats", headers=Ha).json()["balance"]
    r = client.post("/api/dating/likes/reveal", headers=Ha).json()
    assert any(x["userId"] == ub["id"] for x in r["revealed"])
    assert client.get("/api/eclats", headers=Ha).json()["balance"] == before - 30  # ECLATS_REVEAL_LIKES


def test_suppression_rgpd_propagee(client, auth):
    Ha, ua = auth("del-a@divarc.fr")
    Hb, ub = auth("del-b@divarc.fr")
    _profile(client, Ha, "homme", ["femme"])
    _profile(client, Hb, "femme", ["homme"])
    client.post(f"/api/dating/swipe/{ub['id']}", headers=Ha, json={"action": "like"})
    client.post(f"/api/dating/swipe/{ua['id']}", headers=Hb, json={"action": "like"})
    assert client.delete("/api/dating/profile", headers=Ha).json()["ok"] is True
    assert client.get("/api/dating/me", headers=Ha).json()["hasProfile"] is False
    assert client.get("/api/dating/matches", headers=Hb).json() == []  # match supprimé côté B aussi
