"""Use cases 'événements' : création, RSVP (participe/intéressé), listes."""
from __future__ import annotations

from datetime import datetime, timezone

from ...helpers import now as _now
from ..adapters.persistence.models import Event

_RSVP = {"going", "interested", "none"}


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def create_event(uow, owner_id: str, *, title: str, starts_at: str,
                       description: str | None = None, location: str | None = None,
                       online: bool = False, group_id: str | None = None) -> Event:
    if not (title or "").strip():
        raise ValueError("Titre requis")
    try:
        starts = _aware(datetime.fromisoformat(starts_at))
    except (TypeError, ValueError):
        raise ValueError("Date de début invalide (format ISO attendu)")
    e = Event(owner_id=owner_id, title=title.strip()[:160], description=(description or None),
              location=(location or None), online=bool(online), starts_at=starts, group_id=group_id)
    await uow.events.create(e)
    await uow.session.flush()
    await uow.events.set_rsvp(e.id, owner_id, "going")  # l'organisateur participe
    return e


async def rsvp(uow, me: str, event_id: str, status: str) -> None:
    if status not in _RSVP:
        raise ValueError("Statut invalide")
    if not await uow.events.get(event_id):
        raise LookupError("Événement introuvable")
    await uow.events.set_rsvp(event_id, me, None if status == "none" else status)


async def list_events(uow, me: str):
    now_dt = _now()
    return await uow.events.my_events(me, now_dt), await uow.events.upcoming(now_dt)
