"""Use cases 'modération' (Couche 9) : signalement, file manuelle, résolution, transparence.

Confiance-first : signalement + file manuelle humaine + journal de transparence.
Aucune décision automatique de retrait (pas de faux « IA » ici) — un humain tranche.
"""
from __future__ import annotations

from ...helpers import now as _now
from ..adapters.persistence.models import ModerationAction, Report

# Motifs proposés à l'utilisateur (fermé pour éviter le texte libre non structuré).
REASONS = ["spam", "harcelement", "haine", "violence", "nudite", "arnaque", "autre"]
SUBJECT_TYPES = ["post", "comment", "user", "group", "page"]
ACTIONS = ["dismiss", "remove", "warn"]


async def _subject_context(uow, subject_type: str, subject_id: str) -> dict:
    """Instantané minimal du contenu signalé (pour la file, sans re-requêter le contenu supprimé)."""
    ctx: dict = {}
    if subject_type == "post":
        p = await uow.posts.get(subject_id)
        if p:
            ctx = {"authorId": p.author_id, "excerpt": (p.body_text or "")[:140]}
    elif subject_type == "comment":
        c = await uow.comments.get(subject_id)
        if c:
            ctx = {"authorId": c.author_id, "excerpt": (c.body_text or "")[:140]}
    return ctx


async def create_report(uow, reporter_id: str, subject_type: str, subject_id: str,
                        reason: str, details: str | None = None) -> Report:
    if subject_type not in SUBJECT_TYPES:
        raise ValueError("Type de contenu inconnu")
    if reason not in REASONS:
        reason = "autre"
    # Anti-doublon : un seul signalement en attente par (utilisateur, objet).
    existing = await uow.reports.pending_by(reporter_id, subject_type, subject_id)
    if existing:
        return existing
    ctx = await _subject_context(uow, subject_type, subject_id)
    r = Report(reporter_id=reporter_id, subject_type=subject_type, subject_id=subject_id,
               reason=reason, details=(details or "")[:1000] or None, context=ctx)
    await uow.reports.add(r)
    await uow.commit()
    return r


async def queue(uow, status: str = "pending", limit: int = 100) -> list[Report]:
    return await uow.reports.list_by_status(status, limit)


async def _apply_removal(uow, subject_type: str, subject_id: str) -> None:
    """Masque le contenu (soft-delete) selon son type. Idempotent."""
    if subject_type == "post":
        p = await uow.posts.get(subject_id)
        if p and p.deleted_at is None:
            p.deleted_at = _now()
            p.moderation_state = "removed"
    elif subject_type == "comment":
        c = await uow.comments.get(subject_id)
        if c and c.deleted_at is None:
            c.deleted_at = _now()
            c.moderation_state = "removed"


async def resolve_report(uow, moderator_id: str, report_id: str, action: str,
                         note: str | None = None) -> Report:
    r = await uow.reports.get(report_id)
    if not r:
        raise LookupError("Signalement introuvable")
    if action not in ACTIONS:
        raise ValueError("Action inconnue")
    if r.status == "pending":
        if action == "remove":
            await _apply_removal(uow, r.subject_type, r.subject_id)
        r.status = "actioned" if action in ("remove", "warn") else "dismissed"
        r.resolution = action
        r.note = (note or "")[:1000] or None
        r.resolved_by = moderator_id
        r.resolved_at = _now()
        # Journal de transparence
        await uow.moderation.add(ModerationAction(
            moderator_id=moderator_id, action=action, subject_type=r.subject_type,
            subject_id=r.subject_id, reason=r.reason, note=r.note, report_id=r.id))
        await uow.commit()
    return r


async def stats(uow) -> dict:
    return {"reports": await uow.reports.counts_by_status(),
            "actions": await uow.moderation.counts_by_action()}


async def transparency(uow, limit: int = 30) -> dict:
    """Vue PUBLIQUE, agrégée & anonymisée (aucune donnée perso) — que du réel."""
    actions = await uow.moderation.recent(limit)
    return {
        "byAction": await uow.moderation.counts_by_action(),
        "byReason": await uow.moderation.counts_by_reason(),
        "recent": [{"action": a.action, "subjectType": a.subject_type, "reason": a.reason,
                    "at": a.created_at.isoformat()} for a in actions],
    }
