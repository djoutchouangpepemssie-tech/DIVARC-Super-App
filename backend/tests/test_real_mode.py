"""Mode réel (DEMO_MODE=False) : compte propre, aucune donnée fictive."""
import app.config as configmod


def test_nouveau_compte_solde_zero_et_bienvenue_officielle(client, auth, monkeypatch):
    monkeypatch.setattr(configmod.settings, "DEMO_MODE", False)
    H, u = auth("reel@divarc.fr")

    # Solde à 0 € (pas de 4 800 € fictifs)
    assert client.get("/api/wallet", headers=H).json()["balanceCents"] == 0

    # Une seule conversation : le message de bienvenue du compte OFFICIEL DIVARC
    convos = client.get("/api/conversations", headers=H).json()
    assert len(convos) == 1
    assert convos[0]["title"] == "DIVARC"


def test_marche_et_social_vides_en_reel(client, auth, monkeypatch):
    monkeypatch.setattr(configmod.settings, "DEMO_MODE", False)
    H, _ = auth("reel2@divarc.fr")
    assert client.get("/api/market/listings", headers=H).json() == []
    assert client.get("/api/social/feed", headers=H).json() == []


def test_recherche_ne_renvoie_pas_de_faux_amis(client, auth, monkeypatch):
    monkeypatch.setattr(configmod.settings, "DEMO_MODE", False)
    H, _ = auth("reel3@divarc.fr")
    # Aucun bot démo ne doit apparaître (ni le compte officiel, isBot exclu de la recherche)
    res = client.get("/api/discover/search?q=marie", headers=H).json()
    assert res == []
