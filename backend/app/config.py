"""Configuration 12-factor : toutes les valeurs viennent des variables d'environnement."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Base de données (obligatoire) ---
    MONGO_URL: str = "mongodb://localhost:27017"
    # Sur Railway, l'URL interne (*.railway.internal) ne résout pas toujours ; si MONGO_PUBLIC_URL
    # est fournie, on l'utilise en priorité (proxy public, fiable partout).
    MONGO_PUBLIC_URL: str = ""
    DB_NAME: str = "divarc"

    @property
    def mongo_uri(self) -> str:
        return self.MONGO_PUBLIC_URL.strip() or self.MONGO_URL

    # --- Assistant IA (optionnel) ---
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-sonnet-4-5-20250929"

    # --- E-mails OTP via Resend (optionnel) ---
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "DIVARC <onboarding@resend.dev>"

    # --- Géolocalisation (optionnel) ---
    GEOAPIFY_API_KEY: str = ""

    # --- Notifications push Web (VAPID) ---
    # Générées une fois puis stockées en variables Railway. Sans elles, le push est simplement désactivé.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:djoutchouangpepemssie@gmail.com"

    # --- Appels WebRTC : serveur TURN (optionnel, pour fiabiliser les appels en 4G/5G) ---
    # STUN public suffit sur WiFi/même réseau ; ajouter un TURN rend les appels fiables partout.
    TURN_URL: str = ""       # ex: turn:openrelay.metered.ca:80
    TURN_USERNAME: str = ""
    TURN_PASSWORD: str = ""

    # --- Éclats (monnaie interne, sens unique, non convertible en €) ---
    ECLATS_WELCOME: int = 100      # cadeau de bienvenue à l'inscription
    ECLATS_DAILY: int = 10         # check-in quotidien (base)
    ECLATS_DAILY_STREAK_MAX: int = 6   # bonus max ajouté pour une longue série
    ECLATS_REFERRAL: int = 50      # parrainage : Éclats pour le parrain ET le filleul
    ECLATS_CASHBACK_BPS: int = 200  # cashback en Éclats sur les vrais achats (200 = 2,00%)
    ECLATS_BOOST_LISTING: int = 50  # coût en Éclats pour booster une annonce
    ECLATS_BOOST_POST: int = 40     # coût en Éclats pour booster un post social
    ECLATS_BOOST_HOURS: int = 24    # durée d'un boost
    # Rencontres (puits d'Éclats)
    ECLATS_SUPERLIKE: int = 15      # coût d'un super-like
    ECLATS_DATING_BOOST: int = 60   # coût d'un boost de profil Rencontres
    ECLATS_REVEAL_LIKES: int = 30   # coût pour révéler qui t'a liké
    DATING_DAILY_LIKES: int = 30    # likes gratuits par jour (au-delà : super-like ou attendre)
    DATING_MIN_AGE: int = 18

    # --- DIVARC+ (abonnement récurrent) ---
    PLUS_PRICE_CENTS: int = 999      # 9,99 €/mois (débité du wallet € — prêt PSP)
    PLUS_TRIAL_DAYS: int = 7         # essai gratuit une fois
    PLUS_PERIOD_DAYS: int = 30
    PLUS_MONTHLY_ECLATS: int = 200   # Éclats offerts à chaque période
    PLUS_CASHBACK_MULT: int = 2      # cashback multiplié pour les abonnés

    # --- Arcade (jeux de COMPÉTENCE — aucun hasard à gains monétaires) ---
    ARCADE_ENTRY: int = 5            # coût d'une partie en Éclats (après la partie gratuite du jour)
    ARCADE_FREE_DAILY: int = 1       # parties gratuites par jour et par jeu

    # --- Réseau social (bounded context 'social' sur PostgreSQL, cohabite avec Mongo) ---
    # 3 façons de configurer, par ordre de priorité :
    #   1) SOCIAL_DATABASE_URL = URL complète (postgresql://user:pass@host:port/db)
    #   2) DATABASE_URL = repli automatique (fourni par Railway/Heroku)
    #   3) composants séparés SOCIAL_DB_* -> l'URL est assemblée côté serveur, avec le
    #      mot de passe URL-encodé (robuste : évite tous les pièges de références Railway
    #      imbriquées et de caractères spéciaux). On peut y mettre des références simples
    #      Railway comme ${{Postgres.PGPASSWORD}} qui, elles, se résolvent proprement.
    # Vide partout -> SQLite async pour les tests.
    SOCIAL_DATABASE_URL: str = ""
    DATABASE_URL: str = ""  # repli automatique (fourni par Railway/Heroku)
    SOCIAL_DB_HOST: str = ""
    SOCIAL_DB_PORT: str = "5432"
    SOCIAL_DB_USER: str = ""
    SOCIAL_DB_PASSWORD: str = ""
    SOCIAL_DB_NAME: str = ""
    REDIS_URL: str = ""  # pour le temps réel/fan-out à l'échelle (couches ultérieures)
    # Modération plateforme (Couche 9) : emails autorisés à accéder à la file de modération.
    # Liste séparée par des virgules. Vide = aucun modérateur (file inaccessible).
    ADMIN_EMAILS: str = ""

    @property
    def admin_emails_set(self) -> set[str]:
        return {e.strip().lower() for e in (self.ADMIN_EMAILS or "").split(",") if e.strip()}

    @property
    def social_raw_url(self) -> str:
        """L'URL Postgres effective (URL explicite, repli DATABASE_URL, ou composants)."""
        explicit = (self.SOCIAL_DATABASE_URL or "").strip() or (self.DATABASE_URL or "").strip()
        if explicit:
            return explicit
        # Assemblage à partir des composants (mot de passe encodé pour l'URL)
        host = (self.SOCIAL_DB_HOST or "").strip()
        user = (self.SOCIAL_DB_USER or "").strip()
        if host and user:
            from urllib.parse import quote
            pw = quote((self.SOCIAL_DB_PASSWORD or "").strip(), safe="")
            usr = quote(user, safe="")
            port = (self.SOCIAL_DB_PORT or "5432").strip()
            name = (self.SOCIAL_DB_NAME or "").strip() or usr
            return f"postgresql://{usr}:{pw}@{host}:{port}/{name}"
        return ""

    @property
    def social_enabled(self) -> bool:
        """Vrai si une base Postgres est configurée (donc le réseau doit être actif)."""
        return bool(self.social_raw_url)

    @property
    def social_db_url(self) -> str:
        raw = self.social_raw_url
        if not raw:
            return "sqlite+aiosqlite:///:memory:"
        # Normalise vers le driver async
        if raw.startswith("postgres://"):
            raw = "postgresql+asyncpg://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
        return raw

    # --- Mode démo ---
    # False (défaut) = vraie app : nouveaux comptes à 0 €, aucune donnée fictive.
    # True = remplit l'app de contenus de démonstration (faux amis/annonces/vidéos, solde fictif).
    DEMO_MODE: bool = False

    # --- CORS ---
    # Liste d'origines séparées par des virgules, ou "*" pour tout autoriser.
    CORS_ORIGINS: str = "*"

    # --- URL publique du front (pour les QR scannables par appareil photo) ---
    APP_URL: str = "https://www.divarc.fr"

    @property
    def cors_origins_list(self) -> list[str]:
        raw = (self.CORS_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
