"""Couche 6a — Espaces : groupes (adhésion/rôles/validation/visibilité) + stories (24h/vues)."""


def test_groupe_public_adhesion_et_post_reserve_aux_membres(client, auth):
    Ha, ua = auth("g-owner@divarc.fr")
    Hb, ub = auth("g-member@divarc.fr")
    Hc, uc = auth("g-outsider@divarc.fr")
    gid = client.post("/api/net/groups", headers=Ha, json={"name": "Paris", "privacy": "public"}).json()["id"]
    # B rejoint (public -> actif)
    assert client.post(f"/api/net/groups/{gid}/join", headers=Hb).json()["status"] == "active"
    # membre publie dans le groupe ; non-membre non
    assert client.post(f"/api/net/groups/{gid}/posts", headers=Hb, json={"body": "salut le groupe"}).status_code == 200
    assert client.post(f"/api/net/groups/{gid}/posts", headers=Hc, json={"body": "intrus"}).status_code == 403
    # le post de groupe est visible par un membre, pas par un non-membre
    feed_member = client.get(f"/api/net/groups/{gid}/feed", headers=Hb).json()["items"]
    assert any(p["body"] == "salut le groupe" for p in feed_member)


def test_groupe_prive_file_de_validation(client, auth):
    Ha, ua = auth("gp-owner@divarc.fr")
    Hb, ub = auth("gp-req@divarc.fr")
    gid = client.post("/api/net/groups", headers=Ha, json={"name": "Privé", "privacy": "private"}).json()["id"]
    # B demande -> pending
    assert client.post(f"/api/net/groups/{gid}/join", headers=Hb).json()["status"] == "pending"
    # l'admin voit la demande en attente
    mem = client.get(f"/api/net/groups/{gid}/members", headers=Ha).json()
    assert any(u["id"] == ub["id"] for u in mem.get("pending", []))
    # feed privé inaccessible tant que non membre
    assert client.get(f"/api/net/groups/{gid}/feed", headers=Hb).status_code == 404
    # admin approuve -> B devient membre actif et accède au feed
    assert client.post(f"/api/net/groups/{gid}/members/{ub['id']}/approve", headers=Ha).json()["ok"] is True
    assert client.get(f"/api/net/groups/{gid}/feed", headers=Hb).status_code == 200


def test_post_de_groupe_invisible_hors_feed_de_groupe(client, auth):
    Ha, _ = auth("gv-a@divarc.fr")
    Hc, _ = auth("gv-c@divarc.fr")
    gid = client.post("/api/net/groups", headers=Ha, json={"name": "G", "privacy": "public"}).json()["id"]
    pid = client.post(f"/api/net/groups/{gid}/posts", headers=Ha, json={"body": "interne"}).json()["id"]
    # un non-membre ne peut pas voir le post de groupe directement (visibility=group)
    assert client.get(f"/api/net/posts/{pid}", headers=Hc).status_code == 404


def test_moderateur_peut_supprimer_un_post_de_groupe(client, auth):
    Ha, ua = auth("gm-admin@divarc.fr")
    Hb, ub = auth("gm-member@divarc.fr")
    gid = client.post("/api/net/groups", headers=Ha, json={"name": "Mod", "privacy": "public"}).json()["id"]
    client.post(f"/api/net/groups/{gid}/join", headers=Hb)
    pid = client.post(f"/api/net/groups/{gid}/posts", headers=Hb, json={"body": "à modérer"}).json()["id"]
    # l'admin (owner) supprime le post d'un membre
    assert client.delete(f"/api/net/posts/{pid}", headers=Ha).json()["ok"] is True


def test_story_publiee_visible_par_les_suivis_et_vue_enregistree(client, auth):
    Ha, ua = auth("st-a@divarc.fr")
    Hb, ub = auth("st-b@divarc.fr")
    # B suit A
    client.post(f"/api/net/follow/{ua['id']}", headers=Hb)
    sid = client.post("/api/net/stories", headers=Ha, json={"mediaUrl": "/img/s1", "caption": "coucou"}).json()["id"]
    # B voit la story de A dans son fil de stories
    feed = client.get("/api/net/stories", headers=Hb).json()["items"]
    assert any(g["author"]["id"] == ua["id"] for g in feed)
    # B regarde -> vue enregistrée
    assert client.post(f"/api/net/stories/{sid}/view", headers=Hb).status_code == 200
    viewers = client.get(f"/api/net/stories/{sid}/viewers", headers=Ha).json()
    assert viewers["count"] == 1 and any(v["id"] == ub["id"] for v in viewers["items"])


def test_story_non_suivie_refusee(client, auth):
    Ha, ua = auth("st-x@divarc.fr")
    Hc, _ = auth("st-y@divarc.fr")
    sid = client.post("/api/net/stories", headers=Ha, json={"mediaUrl": "/img/s"}).json()["id"]
    # C ne suit pas A -> ne peut pas voir la story
    assert client.post(f"/api/net/stories/{sid}/view", headers=Hc).status_code == 403
