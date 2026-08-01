"""Connexion par nom d'utilisateur (@handle) en plus de l'e-mail, sans créer de doublon."""


def test_connexion_par_nom_utilisateur(client, auth):
    # Compte existant avec un handle choisi
    H, u = auth("perso@divarc.fr")
    client.patch("/api/users/me", headers=H, json={"handle": "moncompte"})

    # On envoie le code en tapant le NOM D'UTILISATEUR (pas l'e-mail)
    send = client.post("/api/auth/otp/send", json={"email": "@moncompte"}).json()
    assert send["isNew"] is False          # compte reconnu -> connexion, pas inscription
    assert "@" in send["sentTo"]           # e-mail masqué renvoyé pour affichage
    assert send["sentTo"] != "perso@divarc.fr"  # jamais l'e-mail en clair complet

    # On vérifie le code avec le nom d'utilisateur -> on retombe sur LE MÊME compte
    r = client.post("/api/auth/otp/verify", json={"email": "moncompte", "code": send["previewCode"]}).json()
    assert r["user"]["id"] == u["id"] and r["isNew"] is False


def test_nom_utilisateur_inconnu_refuse(client, auth):
    auth("autre@divarc.fr")  # au moins un user existe
    r = client.post("/api/auth/otp/send", json={"email": "@inexistant_xyz"})
    assert r.status_code == 400


def test_email_existant_ne_cree_pas_de_doublon(client, auth):
    H, u = auth("unique@divarc.fr")
    # 2e "inscription" avec le même e-mail -> même compte, aucun doublon
    code = client.post("/api/auth/otp/send", json={"email": "unique@divarc.fr"}).json()["previewCode"]
    r = client.post("/api/auth/otp/verify", json={"email": "unique@divarc.fr", "code": code}).json()
    assert r["user"]["id"] == u["id"] and r["isNew"] is False
