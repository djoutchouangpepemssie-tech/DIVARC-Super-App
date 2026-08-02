"""Track A — fan-out on write : livraison rapide MAIS visibilité re-vérifiée à la lecture."""


def test_fanout_livre_le_post_a_un_abonne(client, auth):
    Ha, ua = auth("fo-a@divarc.fr")
    Hb, ub = auth("fo-b@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    pid = client.post("/api/net/posts", headers=Hb, json={"body": "salut le fil"}).json()["id"]
    feed = client.get("/api/net/feed?mode=ranked", headers=Ha).json()["items"]
    assert any(p["id"] == pid for p in feed)


def test_fanout_backfill_si_suivi_apres_publication(client, auth):
    # B publie AVANT que A ne le suive -> le post n'est pas fan-outé vers A, mais le repli
    # pull doit quand même le faire apparaître (robustesse / transition).
    Ha, ua = auth("fo2-a@divarc.fr")
    Hb, ub = auth("fo2-b@divarc.fr")
    pid = client.post("/api/net/posts", headers=Hb, json={"body": "avant le suivi"}).json()["id"]
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    feed = client.get("/api/net/feed?mode=ranked", headers=Ha).json()["items"]
    assert any(p["id"] == pid for p in feed)


def test_visibilite_re_verifiee_amis_seulement(client, auth):
    """Un post 'amis seulement' fan-outé aux abonnés NE DOIT PAS être vu par un simple
    abonné non-ami (la PolicyService reste le garde-fou), mais bien par un ami."""
    Hb, ub = auth("fo3-b@divarc.fr")     # auteur
    Ha, ua = auth("fo3-a@divarc.fr")     # simple abonné (pas ami)
    Hc, uc = auth("fo3-c@divarc.fr")     # ami
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)   # A suit B
    # C et B deviennent amis (demande mutuelle = amitié directe)
    client.post(f"/api/net/friends/request/{uc['id']}", headers=Hb)
    client.post(f"/api/net/friends/request/{ub['id']}", headers=Hc)
    pid = client.post("/api/net/posts", headers=Hb,
                      json={"body": "réservé aux amis", "visibility": "friends"}).json()["id"]
    # A (simple abonné) NE voit PAS le post amis-seulement, malgré le fan-out
    fa = client.get("/api/net/feed?mode=ranked", headers=Ha).json()["items"]
    assert not any(p["id"] == pid for p in fa)
    # C (ami) le voit
    fc = client.get("/api/net/feed?mode=ranked", headers=Hc).json()["items"]
    assert any(p["id"] == pid for p in fc)


def test_bloque_apres_fanout_disparait_du_fil(client, auth):
    Ha, ua = auth("fo4-a@divarc.fr")
    Hb, ub = auth("fo4-b@divarc.fr")
    client.post(f"/api/net/follow/{ub['id']}", headers=Ha)
    pid = client.post("/api/net/posts", headers=Hb, json={"body": "coucou"}).json()["id"]
    # A bloque B APRÈS le fan-out -> le post doit disparaître de son fil
    client.post(f"/api/net/block/{ub['id']}", headers=Ha)
    feed = client.get("/api/net/feed?mode=ranked", headers=Ha).json()["items"]
    assert not any(p["id"] == pid for p in feed)
