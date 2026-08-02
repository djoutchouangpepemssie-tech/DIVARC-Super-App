"""Amélioration Facebook — fil classé : pagination par « déjà-vu », pas de doublon, diversité."""


def _seed_follow_and_posts(client, auth):
    Ha, ua = auth("frk-a@divarc.fr")
    Hb, ub = auth("frk-b@divarc.fr")
    Hc, uc = auth("frk-c@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    client.post(f"/api/net/follow/{uc['id']}", headers=Ha)
    ids = []
    for i in range(3):
        ids.append(client.post("/api/net/posts", headers=Hb, json={"body": f"B{i}"}).json()["id"])
    ids.append(client.post("/api/net/posts", headers=Hc, json={"body": "C0"}).json()["id"])
    return Ha, ids


def test_pagination_sans_doublon_puis_a_jour(client, auth):
    Ha, ids = _seed_follow_and_posts(client, auth)
    seen = []
    # page 1 (limit 2) -> 2 posts + "more"
    p1 = client.get("/api/net/feed?mode=ranked&limit=2", headers=Ha).json()
    assert len(p1["items"]) == 2 and p1["nextCursor"] == "more" and p1["caughtUp"] is False
    seen += [it["id"] for it in p1["items"]]
    # page 2 -> les posts NON encore vus, aucun doublon
    p2 = client.get("/api/net/feed?mode=ranked&limit=2&cursor=more", headers=Ha).json()
    ids2 = [it["id"] for it in p2["items"]]
    assert not set(ids2) & set(seen)  # aucun doublon entre les pages
    seen += ids2
    # au total on a bien vu les 4 posts, sans répétition
    assert len(set(seen)) == 4
    # page suivante -> vide + "à jour"
    p3 = client.get("/api/net/feed?mode=ranked&limit=2&cursor=more", headers=Ha).json()
    assert p3["items"] == [] and p3["caughtUp"] is True


def test_post_deja_vu_ne_reapparait_pas_au_rechargement(client, auth):
    Ha, ids = _seed_follow_and_posts(client, auth)
    first = client.get("/api/net/feed?mode=ranked&limit=10", headers=Ha).json()
    assert len(first["items"]) == 4 and first["caughtUp"] is True
    # rechargement : tout a été vu -> fil « à jour », rien ne se répète
    again = client.get("/api/net/feed?mode=ranked&limit=10", headers=Ha).json()
    assert again["items"] == [] and again["caughtUp"] is True


def test_mode_recent_ignore_le_deja_vu(client, auth):
    Ha, ids = _seed_follow_and_posts(client, auth)
    client.get("/api/net/feed?mode=ranked&limit=10", headers=Ha)  # marque tout comme vu
    # le mode chronologique reste exhaustif (échappatoire) : les posts sont toujours là
    recent = client.get("/api/net/feed?mode=recent&limit=10", headers=Ha).json()
    assert len(recent["items"]) == 4
