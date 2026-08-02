"""Couche 9 — Confiance : signalement, file de modération, transparence, RGPD."""
import app.config as configmod


def _mod(monkeypatch, email):
    monkeypatch.setattr(configmod.settings, "ADMIN_EMAILS", email)


def test_signalement_cree_et_dedup(client, auth):
    Ha, ua = auth("mrep-a@divarc.fr")
    Hb, ub = auth("mrep-b@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "contenu litigieux"}).json()["id"]
    r1 = client.post("/api/net/report", headers=Hb,
                     json={"subjectType": "post", "subjectId": pid, "reason": "spam"}).json()
    assert r1["status"] == "pending"
    # 2e signalement identique -> même signalement (anti-doublon)
    r2 = client.post("/api/net/report", headers=Hb,
                     json={"subjectType": "post", "subjectId": pid, "reason": "spam"}).json()
    assert r2["id"] == r1["id"]


def test_file_reservee_au_moderateur(client, auth):
    Ha, _ = auth("mq-a@divarc.fr")
    assert client.get("/api/net/moderation/queue", headers=Ha).status_code == 403
    # config expose isModerator=false pour un utilisateur normal
    assert client.get("/api/net/moderation/config", headers=Ha).json()["isModerator"] is False


def test_moderateur_voit_file_et_retire(client, auth, monkeypatch):
    _mod(monkeypatch, "boss@divarc.fr")
    Hm, _ = auth("boss@divarc.fr")           # modérateur
    Ha, ua = auth("mm-auteur@divarc.fr")
    Hb, _ = auth("mm-signaleur@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "à retirer"}).json()["id"]
    client.post("/api/net/report", headers=Hb,
                json={"subjectType": "post", "subjectId": pid, "reason": "haine"})
    # le modérateur voit le signalement enrichi
    q = client.get("/api/net/moderation/queue", headers=Hm).json()["items"]
    assert any(it["subjectId"] == pid and it["author"]["id"] == ua["id"] for it in q)
    rid = next(it["id"] for it in q if it["subjectId"] == pid)
    # il retire le contenu
    res = client.post(f"/api/net/moderation/reports/{rid}/resolve", headers=Hm,
                      json={"action": "remove"}).json()
    assert res["status"] == "actioned" and res["resolution"] == "remove"
    # le post n'est plus visible, même pour son auteur
    assert client.get(f"/api/net/posts/{pid}", headers=Ha).status_code == 404
    # le signalement a disparu de la file "pending"
    q2 = client.get("/api/net/moderation/queue", headers=Hm).json()["items"]
    assert all(it["id"] != rid for it in q2)


def test_transparence_publique_agregee(client, auth, monkeypatch):
    _mod(monkeypatch, "boss2@divarc.fr")
    Hm, _ = auth("boss2@divarc.fr")
    Ha, _ = auth("tr-a@divarc.fr")
    Hb, _ = auth("tr-b@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "x"}).json()["id"]
    client.post("/api/net/report", headers=Hb, json={"subjectType": "post", "subjectId": pid, "reason": "spam"})
    q = client.get("/api/net/moderation/queue", headers=Hm).json()["items"]
    rid = next(it["id"] for it in q if it["subjectId"] == pid)
    client.post(f"/api/net/moderation/reports/{rid}/resolve", headers=Hm, json={"action": "remove"})
    # la page publique de transparence montre l'action agrégée (aucune donnée perso)
    t = client.get("/api/net/transparency", headers=Ha).json()
    assert t["byAction"].get("remove", 0) >= 1
    assert all("authorId" not in a and "moderator" not in a for a in t["recent"])


def test_rgpd_export(client, auth):
    Ha, ua = auth("exp-a@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "mon post perso"}).json()["id"]
    client.post(f"/api/net/posts/{pid}/comments", headers=Ha, json={"body": "mon commentaire"})
    data = client.get("/api/net/me/export", headers=Ha).json()
    assert data["userId"] == ua["id"]
    assert data["counts"]["posts"] >= 1 and data["counts"]["comments"] >= 1
    assert any(p["body"] == "mon post perso" for p in data["posts"])


def test_rgpd_effacement_exige_confirmation_puis_supprime(client, auth):
    Ha, ua = auth("era-a@divarc.fr")
    pid = client.post("/api/net/posts", headers=Ha, json={"body": "à oublier"}).json()["id"]
    # sans confirmation -> 400
    assert client.post("/api/net/me/erase", headers=Ha, json={}).status_code == 400
    # avec confirmation -> efface
    res = client.post("/api/net/me/erase", headers=Ha, json={"confirm": "SUPPRIMER"}).json()
    assert res["erased"] is True and res["posts"] >= 1
    # le post n'est plus accessible
    assert client.get(f"/api/net/posts/{pid}", headers=Ha).status_code == 404
    # l'export ne contient plus de post actif
    data = client.get("/api/net/me/export", headers=Ha).json()
    assert all(p["deleted"] for p in data["posts"])
