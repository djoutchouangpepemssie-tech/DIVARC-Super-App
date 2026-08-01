"""Use cases 'graphe social' : amis (demande→acceptation), suivi, blocage, sourdine."""
from __future__ import annotations


async def _make_friends(uow, a: str, b: str) -> None:
    await uow.edges.remove(a, b, "request")
    await uow.edges.remove(b, a, "request")
    await uow.edges.set(a, b, "friend")
    await uow.edges.set(b, a, "friend")


async def send_friend_request(uow, me: str, target: str) -> str:
    if me == target:
        raise ValueError("Action invalide")
    kinds = await uow.edges.kinds_between(me, target)
    if "out:block" in kinds or "in:block" in kinds:
        raise PermissionError("Indisponible")
    if "out:friend" in kinds and "in:friend" in kinds:
        return "friends"
    # si l'autre m'a déjà envoyé une demande -> on devient amis directement
    if await uow.edges.get_status(target, me, "request"):
        await _make_friends(uow, me, target)
        return "friends"
    await uow.edges.set(me, target, "request", "pending")
    return "pending"


async def accept_friend(uow, me: str, requester: str) -> bool:
    if not await uow.edges.get_status(requester, me, "request"):
        raise LookupError("Aucune demande")
    await _make_friends(uow, me, requester)
    return True


async def decline_friend(uow, me: str, requester: str) -> None:
    await uow.edges.remove(requester, me, "request")


async def cancel_request(uow, me: str, target: str) -> None:
    await uow.edges.remove(me, target, "request")


async def unfriend(uow, me: str, other: str) -> None:
    await uow.edges.remove(me, other, "friend")
    await uow.edges.remove(other, me, "friend")


async def follow(uow, me: str, target: str) -> None:
    if me == target:
        raise ValueError("Action invalide")
    kinds = await uow.edges.kinds_between(me, target)
    if "out:block" in kinds or "in:block" in kinds:
        raise PermissionError("Indisponible")
    await uow.edges.set(me, target, "follow")


async def unfollow(uow, me: str, target: str) -> None:
    await uow.edges.remove(me, target, "follow")


async def block(uow, me: str, target: str) -> None:
    for k in ("friend", "follow", "request"):  # rompt toute relation
        await uow.edges.remove(me, target, k)
        await uow.edges.remove(target, me, k)
    await uow.edges.set(me, target, "block")


async def unblock(uow, me: str, target: str) -> None:
    await uow.edges.remove(me, target, "block")


async def mute(uow, me: str, target: str) -> None:
    await uow.edges.set(me, target, "mute")


async def unmute(uow, me: str, target: str) -> None:
    await uow.edges.remove(me, target, "mute")


async def relationship(uow, me: str, other: str) -> dict:
    kinds = await uow.edges.kinds_between(me, other)
    return {
        "friend": "out:friend" in kinds and "in:friend" in kinds,
        "following": "out:follow" in kinds,
        "followsMe": "in:follow" in kinds,
        "requestSent": bool(await uow.edges.get_status(me, other, "request")),
        "requestReceived": bool(await uow.edges.get_status(other, me, "request")),
        "blocked": "out:block" in kinds,
        "muted": "out:mute" in kinds,
    }


async def list_friends(uow, me: str) -> list[str]:
    return await uow.edges.list_out(me, "friend")


async def incoming_requests(uow, me: str) -> list[str]:
    return await uow.edges.list_in(me, "request")


async def outgoing_requests(uow, me: str) -> list[str]:
    return await uow.edges.list_out(me, "request")
