"""Ranking du fil — HEURISTIQUE multi-signaux, DÉTERMINISTE et EXPLICABLE (pas de ML boîte noire).

Inspiré du pipeline Facebook (retrieval → light/heavy rank → re-rank diversité) mais
transparent : chaque post classé expose son « pourquoi ». Objectif DIVARC = interactions
signifiantes, PAS le temps d'écran. Fonctions pures = 100% testables.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankingWeights:
    friend: float = 3.0        # affinité de lien : ami proche
    follow: float = 1.8        # compte suivi
    engagement: float = 2.5    # interactions signifiantes (commentaires > like)
    freshness: float = 1.5     # fraîcheur
    own: float = 0.6           # tes propres publications
    affinity: float = 2.4      # affinité comportementale : à quel point TU interagis avec l'auteur
    media_boost: float = 0.35  # léger bonus formats riches (photo/vidéo)


WEIGHTS = RankingWeights()

# Libellés « Pourquoi je vois ça » (transparence DSA)
REASON_FRIEND = "Un ami proche a publié"
REASON_FOLLOW = "Un compte que tu suis"
REASON_POPULAR = "Populaire en ce moment"
REASON_FRESH = "Fraîchement publié"
REASON_OWN = "Ta publication"
REASON_AFFINITY = "Tu interagis souvent avec cette personne"


def score_post(*, is_friend: bool, is_following: bool, is_own: bool,
               age_hours: float, reactions: int, comments: int,
               affinity: float = 0.0, has_media: bool = False,
               w: RankingWeights = WEIGHTS) -> tuple[float, str]:
    """Retourne (score, raison dominante). Déterministe.

    `affinity` ∈ [0,1] = historique d'interaction viewer→auteur (déjà normalisé).
    """
    freshness = max(0.0, 1.0 - age_hours / 72.0)
    # engagement normalisé : les commentaires (conversation) valent plus que les réactions
    signal = reactions + comments * 2
    engagement = signal / (signal + 8.0)
    aff = max(0.0, min(1.0, affinity))
    factors = {
        REASON_FRIEND: w.friend * (1.0 if is_friend else 0.0),
        REASON_FOLLOW: w.follow * (1.0 if (is_following and not is_friend) else 0.0),
        REASON_POPULAR: w.engagement * engagement,
        REASON_FRESH: w.freshness * freshness,
        REASON_OWN: w.own * (1.0 if is_own else 0.0),
        REASON_AFFINITY: w.affinity * aff,
    }
    score = sum(factors.values()) + (w.media_boost if has_media else 0.0)
    # Ta propre publication est toujours étiquetée comme telle (transparence)
    reason = REASON_OWN if is_own else max(factors.items(), key=lambda kv: kv[1])[0]
    return score, reason


def diversify(scored: list, *, author_penalty: float = 0.45) -> list:
    """Re-rank « diversité » (comme le re-rank Facebook) : évite d'enchaîner plusieurs
    posts du même auteur. Sélection gloutonne — à chaque tour on prend le meilleur score
    APRÈS pénalité exponentielle sur les auteurs déjà placés.

    `scored` = liste de tuples dont [0]=score et [-1]=post (avec .author_id).
    Retourne la même liste, ré-ordonnée.
    """
    remaining = sorted(scored, key=lambda t: t[0], reverse=True)
    out: list = []
    seen_author: dict = {}
    while remaining:
        best_i, best_adj = 0, float("-inf")
        for i, item in enumerate(remaining):
            author = item[-1].author_id
            adj = item[0] * (author_penalty ** seen_author.get(author, 0))
            if adj > best_adj:
                best_adj, best_i = adj, i
        item = remaining.pop(best_i)
        seen_author[item[-1].author_id] = seen_author.get(item[-1].author_id, 0) + 1
        out.append(item)
    return out
