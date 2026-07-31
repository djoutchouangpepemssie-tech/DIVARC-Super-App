"""Tests temps réel : WebSocket, présence, push de message."""


def _token(headers):
    return headers["Authorization"].split()[1]


def test_ws_refuse_token_invalide(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws?token=bidon") as ws:
            ws.receive_json()


def test_ws_presence_et_push_message(client, auth):
    Ha, ua = auth("wsa@divarc.fr")
    Hb, ub = auth("wsb@divarc.fr")

    # Conversation DM A -> B
    conv = client.post("/api/conversations", headers=Ha, json={"type": "dm", "memberHandles": [ub["handle"]]}).json()
    cid = conv["id"]

    with client.websocket_connect(f"/api/ws?token={_token(Hb)}") as wsb:
        # 1er message reçu = état de présence initial
        init = wsb.receive_json()
        assert init["type"] == "presence_state"

        with client.websocket_connect(f"/api/ws?token={_token(Ha)}") as wsa:
            wsa.receive_json()  # presence_state de A
            # B est notifié que A vient de passer en ligne
            ev = wsb.receive_json()
            assert ev["type"] == "presence" and ev["userId"] == ua["id"] and ev["online"] is True

            # A envoie un message -> B le reçoit en direct via WS
            client.post(f"/api/conversations/{cid}/messages", headers=Ha, json={"text": "coucou temps réel"})
            msg_ev = wsb.receive_json()
            assert msg_ev["type"] == "message"
            assert msg_ev["conversationId"] == cid
            assert msg_ev["message"]["text"] == "coucou temps réel"

    # REST présence
    r = client.get(f"/api/presence?ids={ua['id']},{ub['id']}", headers=Hb).json()
    assert ua["id"] in r and ub["id"] in r


def test_presence_requiert_auth(client):
    assert client.get("/api/presence?ids=x").status_code == 401
