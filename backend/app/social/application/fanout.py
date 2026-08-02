"""Fan-out on write (Track A) — pousse un post dans le fil pré-calculé de ses destinataires.

Modèle hybride façon Facebook/Twitter : fan-out on write pour les comptes normaux ; au-delà
de SOCIAL_FANOUT_MAX destinataires (compte « broadcast »), on s'abstient et le repli pull à la
lecture prend le relais. La visibilité EXACTE est TOUJOURS re-vérifiée à la lecture
(PolicyService) : ici on calcule seulement un ensemble de destinataires *candidats*.
"""
from __future__ import annotations

from ...config import settings


async def _recipients(uow, post) -> list[str]:
    if post.author_type == "page":
        return await uow.pages.follower_user_ids(post.author_id)
    vis = post.visibility
    if vis == "only_me":
        return [post.author_id]  # juste soi
    if post.group_id:
        members = await uow.groups.members(post.group_id)
        return [m.user_id for m in members]
    if vis == "circles":
        ids: list[str] = [post.author_id]
        for cid in (post.audience or {}).get("circle_ids") or []:
            ids += await uow.circles.member_ids(cid)
        return ids
    # public | friends | friends_except : amis + abonnés (la policy filtrera friends/except).
    rec = await uow.edges.followers_of(post.author_id)
    rec.append(post.author_id)  # se voir soi-même dans son fil
    return rec


async def fan_out_post(uow, post) -> int:
    """Insère les entrées de fil pour un post. Retourne le nb d'entrées créées (0 si broadcast)."""
    recipients = await _recipients(uow, post)
    if len(set(recipients)) > settings.SOCIAL_FANOUT_MAX:
        return 0  # compte broadcast : pas de pré-calcul, le repli pull servira
    return await uow.feed_entries.fan_out(recipients, post.id, post.author_id, post.created_at)
