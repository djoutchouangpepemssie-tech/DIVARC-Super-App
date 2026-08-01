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
