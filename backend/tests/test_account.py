"""Suppression de compte (exigence Apple 5.1.1(v)) : compte + données effacés, irréversible."""


def test_suppression_compte(client, auth):
    H, u = auth("del-me@divarc.fr")
    # quelques données rattachées
    client.post("/api/net/posts", headers=H, json={"body": "coucou"})
    assert client.get("/api/auth/me", headers=H).status_code == 200
    # sans confirmation -> refus
    assert client.post("/api/account/delete", headers=H, json={}).status_code == 400
    # avec confirmation -> compte supprimé
    r = client.post("/api/account/delete", headers=H, json={"confirm": "SUPPRIMER"}).json()
    assert r["deleted"] is True
    # le token ne donne plus accès (session supprimée)
    assert client.get("/api/auth/me", headers=H).status_code == 401
