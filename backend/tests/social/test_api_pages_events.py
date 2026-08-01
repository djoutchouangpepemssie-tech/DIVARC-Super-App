"""Couche 6b — Pages (publier au nom de la page, abonnés) + Événements (RSVP)."""


def test_page_creation_publication_et_abonnement(client, auth):
    Ha, ua = auth("pg-owner@divarc.fr")
    Hb, ub = auth("pg-follower@divarc.fr")
    pid = client.post("/api/net/pages", headers=Ha, json={"name": "Ma Marque", "category": "Marque"}).json()["id"]
    # l'admin publie au nom de la page ; un tiers non
    post = client.post(f"/api/net/pages/{pid}/posts", headers=Ha, json={"body": "offre du jour"}).json()
    assert post["author"]["isPage"] is True and post["author"]["name"] == "Ma Marque"
    assert client.post(f"/api/net/pages/{pid}/posts", headers=Hb, json={"body": "spam"}).status_code == 403
    # B s'abonne -> le post de la page apparaît dans son fil
    assert client.post(f"/api/net/pages/{pid}/follow", headers=Hb).json()["following"] is True
    bodies = [p["body"] for p in client.get("/api/net/feed", headers=Hb).json()["items"]]
    assert "offre du jour" in bodies


def test_page_feed_public(client, auth):
    Ha, _ = auth("pg2-owner@divarc.fr")
    Hc, _ = auth("pg2-visitor@divarc.fr")
    pid = client.post("/api/net/pages", headers=Ha, json={"name": "Asso"}).json()["id"]
    client.post(f"/api/net/pages/{pid}/posts", headers=Ha, json={"body": "actu asso"})
    # un visiteur (non abonné) voit le fil public de la page
    feed = client.get(f"/api/net/pages/{pid}/feed", headers=Hc).json()["items"]
    assert any(p["body"] == "actu asso" for p in feed)


def test_evenement_creation_et_rsvp(client, auth):
    Ha, ua = auth("ev-owner@divarc.fr")
    Hb, ub = auth("ev-guest@divarc.fr")
    eid = client.post("/api/net/events", headers=Ha, json={
        "title": "Pique-nique", "startsAt": "2027-06-01T12:00:00+00:00", "location": "Paris"}).json()["id"]
    # l'organisateur participe automatiquement
    d = client.get(f"/api/net/events/{eid}", headers=Ha).json()
    assert d["going"] == 1 and d["myRsvp"] == "going" and d["mine"] is True
    # B se dit intéressé
    r = client.post(f"/api/net/events/{eid}/rsvp", headers=Hb, json={"status": "interested"}).json()
    assert r["interested"] == 1 and r["myRsvp"] == "interested"
    # B passe à participe
    r = client.post(f"/api/net/events/{eid}/rsvp", headers=Hb, json={"status": "going"}).json()
    assert r["going"] == 2 and r["interested"] == 0
    # liste des participants
    att = client.get(f"/api/net/events/{eid}/attendees", headers=Ha).json()
    assert any(u["id"] == ub["id"] for u in att["going"])


def test_evenement_apparait_dans_a_venir(client, auth):
    Ha, _ = auth("ev2-a@divarc.fr")
    Hb, _ = auth("ev2-b@divarc.fr")
    client.post("/api/net/events", headers=Ha, json={"title": "Concert", "startsAt": "2027-07-01T20:00:00+00:00"})
    upcoming = client.get("/api/net/events", headers=Hb).json()["upcoming"]
    assert any(e["title"] == "Concert" for e in upcoming)


def test_rsvp_none_retire(client, auth):
    Ha, _ = auth("ev3-a@divarc.fr")
    Hb, _ = auth("ev3-b@divarc.fr")
    eid = client.post("/api/net/events", headers=Ha, json={"title": "Atelier", "startsAt": "2027-08-01T10:00:00+00:00"}).json()["id"]
    client.post(f"/api/net/events/{eid}/rsvp", headers=Hb, json={"status": "going"})
    r = client.post(f"/api/net/events/{eid}/rsvp", headers=Hb, json={"status": "none"}).json()
    assert r["going"] == 1 and r["myRsvp"] is None  # il ne reste que l'organisateur
