# DIVARC iOS — Guide de mise sur l'App Store (sans Mac)

Ce guide te fait passer de « code prêt » à « app testable sur ton iPhone puis publiée ».
Tu n'as **pas besoin de Mac** : la compilation se fait dans le cloud (Codemagic).

---

## 0. Ce qui est déjà fait (par le code)
- App native iOS (Capacitor) qui emballe DIVARC.
- Version iOS **gratuite et conforme** : wallet €, abonnement et achat d'Éclats **masqués**.
- Fonctions natives : **Face ID**, notifications push, haptique, splash, icônes.
- **Suppression de compte** in-app, Privacy Manifest, textes d'autorisation, liens légaux.
- Pipeline de build cloud (`codemagic.yaml`) + config iOS (`scripts/ios-configure.sh`).

## 1. Compte Apple Developer (toi) — ~15 min + validation Apple
1. Va sur https://developer.apple.com/programs/ → **Enroll**.
2. Paie les **99 $/an**. Pour un compte **organisation** (nom d'entreprise affiché sur l'App Store),
   Apple demande un numéro **D-U-N-S** (gratuit). Pour un compte **individuel**, c'est immédiat.
3. Attends la validation Apple (quelques heures à 2 jours).

## 2. Créer l'app dans App Store Connect (toi) — 10 min
1. https://appstoreconnect.apple.com → **Mes apps** → **+** → **Nouvelle app**.
2. Plateforme **iOS**, nom **DIVARC**, langue **Français**, **Bundle ID** = `fr.divarc.app`
   (crée-le d'abord dans *Certificates, Identifiers & Profiles* → Identifiers si besoin).
3. Catégorie : **Réseaux sociaux**. Note l'**Apple ID numérique** de l'app (10 chiffres) :
   tu le mettras dans `codemagic.yaml` (`APP_STORE_APPLE_ID`).
4. **Classement par âge** : réponds au questionnaire → l'app contient des rencontres → **17+**.

## 3. Clé API App Store Connect (toi) — 5 min
1. App Store Connect → **Utilisateurs et accès** → **Clés** (API) → **+** → rôle **App Manager**.
2. Télécharge le fichier **.p8** (une seule fois !), note le **Key ID** et l'**Issuer ID**.

## 4. Configurer Codemagic (toi + moi) — 15 min
1. Crée un compte sur https://codemagic.io (connexion via GitHub) et **ajoute le dépôt** DIVARC.
2. **Teams → Integrations → App Store Connect** → ajoute la clé (.p8 + Key ID + Issuer ID).
   Donne-lui un nom, puis mets ce nom dans `codemagic.yaml` (`integrations.app_store_connect`).
3. **Environment variables** → groupe **`divarc`** → ajoute `NEXT_PUBLIC_API_BASE` =
   l'URL publique du backend (ex. `https://www.divarc.fr`).
4. Dans `codemagic.yaml`, remplace `APP_STORE_APPLE_ID: 0000000000` par l'Apple ID numérique (étape 2.3).
5. Lance le workflow **« DIVARC iOS – App Store »**. À la fin, le build part sur **TestFlight**.

## 5. Tester sur ton iPhone — 5 min
1. Installe l'app **TestFlight** depuis l'App Store.
2. Dans App Store Connect → **TestFlight**, ajoute-toi comme testeur → tu reçois l'invitation.
3. Ouvre DIVARC sur ton iPhone et vérifie tout (connexion, réseau, Face ID, notifications…).

## 6. Préparer la review App Store (toi) — 20 min
Dans App Store Connect, page de l'app :
- **Confidentialité de l'app** : remplis le questionnaire (email, nom, photos, contenu, position
  approximative → tous « liés à l'utilisateur », **aucun tracking**). Aligne-le sur `PrivacyInfo.xcprivacy`.
- **URL de politique de confidentialité** : `https://www.divarc.fr/confidentialite` ⚠️ **à créer**
  (page publique). Idem conditions `/conditions`. Je peux t'aider à rédiger les textes.
- **Compte de démonstration** pour les évaluateurs (email + accès) : indispensable (l'app exige une connexion).
- **Captures d'écran** iPhone 6.7" et 6.5" (je peux te les générer depuis l'app).
- **Description, mots-clés, support URL**.
- **Note aux évaluateurs** : précise que le wallet €/abonnement sont désactivés sur iOS (app gratuite),
  et où trouver la suppression de compte (**Profil → Supprimer le compte**).
- Quand tout est vert : **Soumettre pour examen**. (Dans `codemagic.yaml`, tu pourras passer
  `submit_to_app_store: true`.)

---

## ⚠️ À finaliser côté backend (moi, quand tu veux)
- **Notifications push APNs** : l'app enregistre déjà le jeton (`/push/register-native`), mais l'**envoi**
  APNs nécessite une **clé APNs (.p8)** côté serveur + l'endpoint d'émission. À brancher pour que les
  push arrivent réellement sur iPhone. (La registration ne casse rien en attendant.)
- **CORS** : autoriser l'origine de l'app native (`capacitor://localhost`) sur le backend si besoin.
- Pages légales `/confidentialite` et `/conditions` à publier sur divarc.fr.

## Rappels utiles
- Le **web n'est jamais impacté** : `npm run build` = web normal ; `npm run build:native` = app.
- Bundle ID : **fr.divarc.app**. Change-le partout si tu en veux un autre.
- Chaque mise à jour = nouveau build Codemagic → TestFlight → (option) App Store.
