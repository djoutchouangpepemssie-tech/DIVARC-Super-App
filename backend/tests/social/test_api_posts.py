"""Couche 2 — API réseau social : publier, feed (curseur), visibilité par post, éditer, supprimer.

Le graphe (amis/suivi) est en Couche 4 ; ici on crée les arêtes directement en base pour
tester la visibilité de bout en bout via l'API.
"""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.social.adapters.persistence import models as m


def _add_edges(*edges):
    """Insère des arêtes (src, dst, kind) via un moteur SÉPARÉ vers le même fichier SQLite
    (évite de toucher au moteur/boucle de l'app)."""
    async def go():
        eng = create_async_engine(settings.social_db_url)
        sm = async_sessionmaker(eng, expire_on_commit=False)
        async with sm() as s:
            for src, dst, kind in edges:
                s.add(m.Edge(src=src, dst=dst, kind=kind))
            await s.commit()
        await eng.dispose()
    asyncio.run(go())


def test_publier_et_relire_son_post(client, auth):
    H, u = auth("net-a@divarc.fr")
    r = client.post("/api/net/posts", headers=H, json={"body": "Bonjour DIVARC", "visibility": "public",
                    "media": [{"url": "/api/chat/media/x", "alt": "une photo"}]}).json()
    assert r["author"]["id"] == u["id"] and r["body"] == "Bonjour DIVARC"
    assert r["media"][0]["alt"] == "une photo" and r["mine"] is True
    got = client.get(f"/api/net/posts/{r['id']}", headers=H).json()
    assert got["id"] == r["id"]


def test_publication_vide_refusee(client, auth):
    H, _ = auth("net-empty@divarc.fr")
    assert client.post("/api/net/posts", headers=H, json={"body": "   "}).status_code == 400


def test_feed_montre_soi_et_les_suivis(client, auth):
    Ha, ua = auth("feed-me@divarc.fr")
    Hb, ub = auth("feed-friend@divarc.fr")
    Hc, uc = auth("feed-stranger@divarc.fr")
    # je suis ub, pas uc
    _add_edges((ua["id"], ub["id"], "follow"))
    client.post("/api/net/posts", headers=Ha, json={"body": "moi"})
    client.post("/api/net/posts", headers=Hb, json={"body": "ami suivi"})
    client.post("/api/net/posts", headers=Hc, json={"body": "inconnu"})
    bodies = [p["body"] for p in client.get("/api/net/feed", headers=Ha).json()["items"]]
    assert "moi" in bodies and "ami suivi" in bodies and "inconnu" not in bodies


def test_visibilite_amis_seulement(client, auth):
    Ha, ua = auth("vis-author@divarc.fr")
    Hb, ub = auth("vis-friend@divarc.fr")
    Hc, uc = auth("vis-follower@divarc.fr")
    # ub est AMI de ua (arêtes bidirectionnelles) ; uc ne fait que suivre
    _add_edges((ua["id"], ub["id"], "friend"), (ub["id"], ua["id"], "friend"),
               (ub["id"], ua["id"], "follow"),  # pour l'avoir dans le feed de ub
               (uc["id"], ua["id"], "follow"))
    post = client.post("/api/net/posts", headers=Ha, json={"body": "entre amis", "visibility": "friends"}).json()
    # l'ami voit
    assert client.get(f"/api/net/posts/{post['id']}", headers=Hb).status_code == 200
    # le simple suiveur ne voit pas
    assert client.get(f"/api/net/posts/{post['id']}", headers=Hc).status_code == 404


def test_feed_pagination_par_curseur(client, auth):
    H, u = auth("cursor@divarc.fr")
    for i in range(5):
        client.post("/api/net/posts", headers=H, json={"body": f"p{i}"})
    page1 = client.get("/api/net/feed?limit=2", headers=H).json()
    assert len(page1["items"]) == 2 and page1["nextCursor"]
    page2 = client.get(f"/api/net/feed?limit=2&cursor={page1['nextCursor']}", headers=H).json()
    ids1 = {p["id"] for p in page1["items"]}
    ids2 = {p["id"] for p in page2["items"]}
    assert len(page2["items"]) == 2 and ids1.isdisjoint(ids2)  # pas de doublon entre pages


def test_editer_et_supprimer_reserve_a_l_auteur(client, auth):
    Ha, ua = auth("edit-a@divarc.fr")
    Hb, ub = auth("edit-b@divarc.fr")
    post = client.post("/api/net/posts", headers=Ha, json={"body": "v1"}).json()
    # un autre ne peut pas éditer (interdit -> 403)
    assert client.patch(f"/api/net/posts/{post['id']}", headers=Hb, json={"body": "hack"}).status_code == 403
    # l'auteur édite -> editedAt renseigné
    ed = client.patch(f"/api/net/posts/{post['id']}", headers=Ha, json={"body": "v2"}).json()
    assert ed["body"] == "v2" and ed["editedAt"]
    # l'auteur supprime -> le post disparaît
    assert client.delete(f"/api/net/posts/{post['id']}", headers=Ha).json()["ok"] is True
    assert client.get(f"/api/net/posts/{post['id']}", headers=Ha).status_code == 404
