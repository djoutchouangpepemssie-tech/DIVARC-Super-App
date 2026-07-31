# Déploiement DIVARC sur Railway — Frontend Next.js + Backend Python + MongoDB

L'application est désormais **découpée en deux services**, conformément à la vision
DIVARC (**toute la logique métier en Python**) :

```
┌──────────────────────────┐      /api/* (proxy)     ┌───────────────────────────┐      ┌──────────────┐
│  Service "web"           │  ───────────────────▶   │  Service "api"            │ ───▶ │  MongoDB     │
│  Frontend Next.js (PWA)  │                          │  Backend Python (FastAPI) │      │  (Railway)   │
│  Root: /                 │                          │  Root: backend/           │      └──────────────┘
└──────────────────────────┘                          └───────────────────────────┘
```

- Le **frontend** (`app/`, `components/`, …) ne contient **aucune logique métier**. Il relaie
  toutes les requêtes `/api/*` vers le backend Python via un *rewrite* Next.js (voir
  [`next.config.js`](next.config.js)). Aucun souci de CORS, et les images fonctionnent tel quel.
- Le **backend** ([`backend/`](backend/)) est une API **FastAPI** qui porte les ~55 routes
  (`/api/auth`, `/api/wallet`, `/api/social`, `/api/market`, `/api/ads`, `/api/store`,
  `/api/admin`, `/api/ai`, …) et parle à **MongoDB** via Motor.

> ✅ Plus aucune dépendance Emergent. ✅ Backend 100 % Python. Le test bout-en-bout
> (`backend/_e2e_test.py`) valide le parcours critique (auth OTP → wallet → messagerie →
> P2P → enveloppe → social → marketplace → store → admin).

---

## Étape 1 — Base MongoDB

Dans un projet Railway : **+ New → Database → Add MongoDB**. Railway expose une variable
`MONGO_URL` sur ce service.

## Étape 2 — Service backend Python (`api`)

1. **+ New → GitHub Repo** → ce dépôt.
2. Dans **Settings → Root Directory**, mettre **`backend`**. Railway lit alors
   [`backend/railway.toml`](backend/railway.toml) (build via `Dockerfile`, démarrage `uvicorn`).
3. **Variables** du service `api` :

   | Variable | Valeur | Requis |
   |---|---|---|
   | `MONGO_URL` | `${{MongoDB.MONGO_URL}}` | ✅ |
   | `DB_NAME` | `divarc` | ✅ |
   | `ANTHROPIC_API_KEY` | clé [console.anthropic.com](https://console.anthropic.com/) | ⬜ assistant IA |
   | `RESEND_API_KEY` / `RESEND_FROM` | clé [resend.com](https://resend.com/) | ⬜ e-mails OTP |
   | `GEOAPIFY_API_KEY` | clé [geoapify.com](https://www.geoapify.com/) | ⬜ géo |
   | `CORS_ORIGINS` | `*` (proxy) | ⬜ |

4. **Settings → Networking → Generate Domain** → note l'URL, ex.
   `https://divarc-api.up.railway.app`. Vérifie `…/api/health`.

## Étape 3 — Service frontend Next.js (`web`)

1. **+ New → GitHub Repo** → le même dépôt (nouveau service).
2. **Root Directory** = `/` (racine). Railway détecte Next.js (Nixpacks, `yarn build` + `yarn start`).
3. **Variables** du service `web` :

   | Variable | Valeur |
   |---|---|
   | `BACKEND_URL` | l'URL du service `api`, ex. `https://divarc-api.up.railway.app` |
   | `NEXT_PUBLIC_WS_URL` | l'URL WebSocket du backend, ex. `wss://divarc-api.up.railway.app` |

   > `BACKEND_URL` alimente le *rewrite* `/api/:path*` → `${BACKEND_URL}/api/:path*` (HTTP).
   > `NEXT_PUBLIC_WS_URL` est utilisé par le navigateur pour la connexion **temps réel**
   > (messagerie instantanée + présence). Les WebSockets ne passent pas par le rewrite : le
   > navigateur se connecte directement au backend en `wss://…/api/ws`. Railway supporte
   > nativement les WebSockets. En local, laisse cette variable vide (fallback auto vers `:8000`).

4. **Generate Domain** → l'URL publique de l'app (celle que tu partages).

## Étape 4 — Vérifier

- `https://API/api/health` → `{"service":"DIVARC API","status":"live",...}`
- `https://WEB/` → onboarding DIVARC ; l'inscription par e-mail marche en **mode preview**
  (le code OTP est renvoyé dans la réponse) tant que `RESEND_API_KEY` n'est pas défini.

---

## Développement local

**Backend :**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env                                 # renseigner MONGO_URL / DB_NAME
uvicorn app.main:app --reload --port 8000            # http://localhost:8000/api/health
```

**MongoDB local (Docker) :** `docker run -d -p 27017:27017 --name divarc-mongo mongo:7`

**Frontend :**
```bash
yarn install
BACKEND_URL=http://localhost:8000 yarn dev           # http://localhost:3000
```

**Tests automatisés du backend (MongoDB en mémoire, sans Docker) :**
```bash
cd backend && pip install mongomock-motor pytest pytest-asyncio && python -m pytest
```

---

## Publier

```bash
git add -A
git commit -m "feat: backend Python (FastAPI) + front proxy — suppression du backend Node"
git push origin main
```
Railway redéploie les deux services à chaque push.
