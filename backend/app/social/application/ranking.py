"""Ranking du fil — baseline HEURISTIQUE, DÉTERMINISTE et EXPLICABLE (pas de ML boîte noire).

Objectif DIVARC : interactions signifiantes, PAS le temps d'écran. Chaque post classé
expose son « pourquoi ». Pondérations en config (ajustables). Fonction pure = 100% testable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankingWeights:
    friend: float = 3.0        # affinité : ami proche
    follow: float = 1.8        # compte suivi
    engagement: float = 2.5    # interactions signifiantes (commentaires pèsent plus que like)
    freshness: float = 1.5     # fraîcheur
    own: float = 0.6           # tes propres publications


WEIGHTS = RankingWeights()

# Libellés « Pourquoi je vois ça » (transparence DSA)
REASON_FRIEND = "Un ami proche a publié"
REASON_FOLLOW = "Un compte que tu suis"
REASON_POPULAR = "Populaire en ce moment"
REASON_FRESH = "Fraîchement publié"
REASON_OWN = "Ta publication"


def score_post(*, is_friend: bool, is_following: bool, is_own: bool,
               age_hours: float, reactions: int, comments: int,
               w: RankingWeights = WEIGHTS) -> tuple[float, str]:
    """Retourne (score, raison dominante). Déterministe."""
    freshness = max(0.0, 1.0 - age_hours / 72.0)
    # engagement normalisé : les commentaires (conversation) valent plus que les réactions
    signal = reactions + comments * 2
    engagement = signal / (signal + 8.0)
    factors = {
        REASON_FRIEND: w.friend * (1.0 if is_friend else 0.0),
        REASON_FOLLOW: w.follow * (1.0 if (is_following and not is_friend) else 0.0),
        REASON_POPULAR: w.engagement * engagement,
        REASON_FRESH: w.freshness * freshness,
        REASON_OWN: w.own * (1.0 if is_own else 0.0),
    }
    score = sum(factors.values())
    # Ta propre publication est toujours étiquetée comme telle (transparence)
    reason = REASON_OWN if is_own else max(factors.items(), key=lambda kv: kv[1])[0]
    return score, reason
