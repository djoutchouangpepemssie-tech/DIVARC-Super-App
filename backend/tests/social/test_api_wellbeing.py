"""Couche 10 — Éclats sociaux + bien-être (fil apaisé, masquage des compteurs)."""


def test_eclats_premiere_publication_du_jour(client, auth):
    Ha, ua = auth("wb-eclat@divarc.fr")
    # 1re publication du jour -> Éclats gagnés
    r1 = client.post("/api/net/posts", headers=Ha, json={"body": "bonjour"}).json()
    assert r1.get("eclatsEarned", 0) >= 1
    # 2e publication -> plus de récompense (plafond 1/jour, idempotent)
    r2 = client.post("/api/net/posts", headers=Ha, json={"body": "encore"}).json()
    assert "eclatsEarned" not in r2
    # le solde d'Éclats reflète le gain
    bal = client.get("/api/eclats", headers=Ha).json()["balance"]
    assert bal >= 1


def test_prefs_bien_etre_get_put(client, auth):
    Ha, _ = auth("wb-prefs@divarc.fr")
    d = client.get("/api/net/wellbeing/prefs", headers=Ha).json()
    assert d["calmMode"] is False and d["hideCounts"] is False
    client.put("/api/net/wellbeing/prefs", headers=Ha, json={"calmMode": True, "hideCounts": True})
    d2 = client.get("/api/net/wellbeing/prefs", headers=Ha).json()
    assert d2["calmMode"] is True and d2["hideCounts"] is True


def test_mode_apaise_masque_les_compteurs_et_force_le_chrono(client, auth):
    Ha, _ = auth("wb-calm-a@divarc.fr")
    Hb, ub = auth("wb-calm-b@divarc.fr")
    # A suit B, B publie et reçoit une réaction de A
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    pid = client.post("/api/net/posts", headers=Hb, json={"body": "coucou"}).json()["id"]
    client.put(f"/api/net/posts/{pid}/reactions", headers=Ha, json={"type": "like"})
    # sans mode apaisé : le total de réactions est un nombre
    feed = client.get("/api/net/feed?mode=ranked", headers=Ha).json()
    post = next(p for p in feed["items"] if p["id"] == pid)
    assert post["reactions"]["total"] == 1
    # active le mode apaisé
    client.put("/api/net/wellbeing/prefs", headers=Ha, json={"calmMode": True})
    feed2 = client.get("/api/net/feed?mode=ranked", headers=Ha).json()
    assert feed2["calm"] is True and feed2["mode"] == "recent"  # forcé en chrono
    post2 = next(p for p in feed2["items"] if p["id"] == pid)
    assert post2["reactions"]["total"] is None and post2["countsHidden"] is True


def test_hide_counts_seul_sans_calm(client, auth):
    Ha, _ = auth("wb-hc-a@divarc.fr")
    Hb, ub = auth("wb-hc-b@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    pid = client.post("/api/net/posts", headers=Hb, json={"body": "hello"}).json()["id"]
    client.put("/api/net/wellbeing/prefs", headers=Ha, json={"hideCounts": True})
    feed = client.get("/api/net/feed?mode=ranked", headers=Ha).json()
    assert feed["calm"] is False  # pas de mode apaisé, juste les compteurs masqués
    post = next(p for p in feed["items"] if p["id"] == pid)
    assert post["countsHidden"] is True and post["commentCount"] is None


def test_feed_caught_up(client, auth):
    Ha, _ = auth("wb-caught@divarc.fr")
    feed = client.get("/api/net/feed?mode=recent", headers=Ha).json()
    # fil vide/court -> pas de page suivante -> "à jour"
    assert feed["caughtUp"] is True and feed["nextCursor"] is None
