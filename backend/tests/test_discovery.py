"""Tests du module Découverte & ajout d'utilisateurs (recherche, contacts hachés, invites, proximité, demandes, blocage)."""
from app.helpers import hash_email, hash_phone


# ---------------- @handle & profil ----------------

def test_handle_available_et_modif_unique(client, auth):
    H, _ = auth("h1@divarc.fr")
    # dispo
    assert client.get("/api/handle/available?handle=super_arielle", headers=H).json()["available"] is True
    # format invalide
    assert client.get("/api/handle/available?handle=ab", headers=H).json()["available"] is False
    # changer le handle
    r = client.patch("/api/users/me", headers=H, json={"handle": "super_arielle"}).json()
    assert r["handle"] == "@super_arielle" and r["handleChanged"] is True
    # 2e changement refusé
    assert client.patch("/api/users/me", headers=H, json={"handle": "autre_nom"}).status_code == 409


def test_recherche_par_handle_et_nom(client, auth):
    Ha, _ = auth("searcher@divarc.fr")
    Hb, ub = auth("target@divarc.fr")
    client.patch("/api/users/me", headers=Hb, json={"name": "Arielle Dupont", "handle": "arielle_d"})
    # par handle
    res = client.get("/api/discover/search?q=arielle_d", headers=Ha).json()
    assert any(u["id"] == ub["id"] for u in res)
    # par nom
    res2 = client.get("/api/discover/search?q=arielle", headers=Ha).json()
    assert any(u["id"] == ub["id"] for u in res2)


def test_recherche_ne_se_retourne_pas_soi_meme(client, auth):
    H, u = auth("self@divarc.fr")
    client.patch("/api/users/me", headers=H, json={"name": "Solo Unique"})
    res = client.get("/api/discover/search?q=solo", headers=H).json()
    assert all(x["id"] != u["id"] for x in res)


# ---------------- Contacts hachés (opt-in) ----------------

def test_contacts_match_par_telephone_optin(client, auth):
    Ha, _ = auth("me@divarc.fr")
    Hb, ub = auth("friend@divarc.fr")
    # B ajoute son numéro et active la découverte par téléphone
    client.patch("/api/users/me", headers=Hb, json={"phone": "06 12 34 56 78", "discoverable": {"byPhone": True}})
    # A (client) envoie le HACHÉ du numéro de B (jamais le numéro en clair)
    res = client.post("/api/discover/contacts/match", headers=Ha,
                      json={"phoneHashes": [hash_phone("+33612345678")]}).json()
    assert any(u["id"] == ub["id"] for u in res)  # matche malgré le format différent


def test_contacts_match_respecte_optin_desactive(client, auth):
    Ha, _ = auth("me2@divarc.fr")
    Hb, ub = auth("friend2@divarc.fr")
    # B ajoute son numéro mais N'ACTIVE PAS byPhone
    client.patch("/api/users/me", headers=Hb, json={"phone": "0798765432"})
    res = client.post("/api/discover/contacts/match", headers=Ha,
                      json={"phoneHashes": [hash_phone("0798765432")]}).json()
    assert all(u["id"] != ub["id"] for u in res)  # non trouvable car opt-in désactivé


def test_contacts_match_par_email_optin(client, auth):
    Ha, _ = auth("me3@divarc.fr")
    Hb, ub = auth("byemail@divarc.fr")
    client.patch("/api/users/me", headers=Hb, json={"discoverable": {"byEmail": True}})
    res = client.post("/api/discover/contacts/match", headers=Ha,
                      json={"emailHashes": [hash_email("BYEMAIL@divarc.fr")]}).json()
    assert any(u["id"] == ub["id"] for u in res)


# ---------------- Invitations + bonus wallet ----------------

def test_invitation_donne_un_bonus_wallet(client, auth):
    Ha, ua = auth("inviter@divarc.fr")
    inv = client.post("/api/discover/invite", headers=Ha).json()
    assert inv["link"].endswith(inv["code"]) or inv["code"] in inv["link"]
    # solde avant
    before = client.get("/api/wallet", headers=Ha).json()["balanceCents"]
    # un nouvel utilisateur s'inscrit via le lien d'invitation
    code = client.post("/api/auth/otp/send", json={"email": "invited@divarc.fr"}).json()["previewCode"]
    client.post("/api/auth/otp/verify", json={"email": "invited@divarc.fr", "code": code, "invite": inv["code"]})
    # l'invitant a reçu +5,00 €
    after = client.get("/api/wallet", headers=Ha).json()["balanceCents"]
    assert after == before + 500


# ---------------- Profil public / lien ----------------

def test_profil_public_par_handle(client, auth):
    Ha, _ = auth("viewer@divarc.fr")
    Hb, ub = auth("public@divarc.fr")
    client.patch("/api/users/me", headers=Hb, json={"handle": "publicguy"})
    r = client.get("/api/discover/user/publicguy", headers=Ha).json()
    assert r["id"] == ub["id"] and r["handle"] == "@publicguy"


# ---------------- Proximité ----------------

def test_proximite_ping_et_liste(client, auth):
    Ha, _ = auth("near-a@divarc.fr")
    Hb, ub = auth("near-b@divarc.fr")
    # les deux pinguent Paris (proches)
    client.post("/api/discover/nearby/ping", headers=Ha, json={"lat": 48.8566, "lon": 2.3522})
    client.post("/api/discover/nearby/ping", headers=Hb, json={"lat": 48.8570, "lon": 2.3525})
    res = client.get("/api/discover/nearby", headers=Ha).json()
    assert any(u["id"] == ub["id"] for u in res)


def test_proximite_requiert_ping(client, auth):
    Ha, _ = auth("near-c@divarc.fr")
    assert client.get("/api/discover/nearby", headers=Ha).status_code == 400


# ---------------- Demandes d'ajout ----------------

def test_demande_ajout_et_acceptation(client, auth):
    Ha, ua = auth("req-a@divarc.fr")
    Hb, ub = auth("req-b@divarc.fr")
    # A envoie une demande à B
    assert client.post(f"/api/discover/request/{ub['id']}", headers=Ha).json()["status"] == "pending_out"
    # B voit la demande
    reqs = client.get("/api/discover/requests", headers=Hb).json()
    assert any(r["id"] == ua["id"] for r in reqs)
    # B accepte -> contact mutuel
    client.post(f"/api/discover/request/{ua['id']}/respond", headers=Hb, json={"action": "accept"})
    assert any(c["id"] == ub["id"] for c in client.get("/api/discover/contacts", headers=Ha).json())
    assert any(c["id"] == ua["id"] for c in client.get("/api/discover/contacts", headers=Hb).json())


# ---------------- Blocage ----------------

def test_blocage_empeche_le_dm(client, auth):
    Ha, ua = auth("blocker@divarc.fr")
    Hb, ub = auth("blocked@divarc.fr")
    client.post(f"/api/discover/block/{ub['id']}", headers=Ha)
    # B ne peut plus démarrer de DM avec A
    r = client.post("/api/conversations", headers=Hb, json={"type": "dm", "memberHandles": [ua["handle"]]})
    assert r.status_code == 403
    # A ne voit plus B dans la recherche
    client.patch("/api/users/me", headers=Hb, json={"name": "Bloque Personne"})
    res = client.get("/api/discover/search?q=bloque", headers=Ha).json()
    assert all(x["id"] != ub["id"] for x in res)
