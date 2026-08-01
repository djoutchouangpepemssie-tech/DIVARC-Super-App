"""Tests de la suppression de messages : pour moi (masqué) / pour tout le monde (tombstone)."""


def _dm(client, auth):
    Ha, ua = auth("da@divarc.fr")
    Hb, ub = auth("db@divarc.fr")
    cid = client.post("/api/conversations", headers=Ha, json={"type": "dm", "memberHandles": [ub["handle"]]}).json()["id"]
    mid = client.post(f"/api/conversations/{cid}/messages", headers=Ha, json={"text": "à supprimer"}).json()["message"]["id"]
    return Ha, Hb, cid, mid


def test_supprimer_pour_moi_masque_uniquement_pour_moi(client, auth):
    Ha, Hb, cid, mid = _dm(client, auth)
    assert client.post(f"/api/messages/{mid}/delete", headers=Ha, json={"scope": "me"}).status_code == 200
    # A ne le voit plus
    msgs_a = client.get(f"/api/conversations/{cid}/messages", headers=Ha).json()["messages"]
    assert all(x["id"] != mid for x in msgs_a)
    # B le voit toujours
    msgs_b = client.get(f"/api/conversations/{cid}/messages", headers=Hb).json()["messages"]
    assert any(x["id"] == mid for x in msgs_b)


def test_supprimer_pour_tout_le_monde_laisse_une_tombstone(client, auth):
    Ha, Hb, cid, mid = _dm(client, auth)
    assert client.post(f"/api/messages/{mid}/delete", headers=Ha, json={"scope": "all"}).status_code == 200
    msgs_b = client.get(f"/api/conversations/{cid}/messages", headers=Hb).json()["messages"]
    tomb = next(x for x in msgs_b if x["id"] == mid)
    assert tomb["deleted"] is True and (tomb.get("text") or "") == ""


def test_seul_expediteur_supprime_pour_tout_le_monde(client, auth):
    Ha, Hb, cid, mid = _dm(client, auth)
    # B (destinataire) ne peut pas supprimer pour tout le monde
    assert client.post(f"/api/messages/{mid}/delete", headers=Hb, json={"scope": "all"}).status_code == 403
