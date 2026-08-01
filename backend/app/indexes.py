"""Création idempotente et tolérante des index MongoDB au démarrage (perf + intégrité).

Un index qui échoue (ex. doublon historique sur une base existante) est journalisé
mais n'empêche jamais le démarrage de l'application.
"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

# (collection, clés, options)
_INDEXES: list[tuple[str, object, dict]] = [
    # Identité & sessions
    ("users", "id", {"unique": True}),
    ("users", "email", {"unique": True, "sparse": True}),
    ("users", "handle", {"unique": True, "sparse": True}),
    ("sessions", "token", {"unique": True}),
    ("sessions", "userId", {}),
    ("otp_codes", "email", {"unique": True}),
    ("otp_codes", "expiresAt", {"expireAfterSeconds": 0}),  # TTL : purge auto des OTP expirés

    # Wallet & finances
    ("wallets", "userId", {"unique": True}),
    ("coffres", "userId", {}),
    ("transactions", [("userId", 1), ("createdAt", -1)], {}),
    ("transactions", [("userId", 1), ("idempotencyKey", 1)], {"sparse": True}),
    ("ledger", "batch", {}),
    ("enveloppes", "id", {"unique": True}),

    # Messagerie
    ("conversations", "id", {"unique": True}),
    ("conversations", "memberIds", {}),
    ("conversations", [("type", 1), ("isPublic", 1)], {}),
    ("messages", [("conversationId", 1), ("createdAt", 1)], {}),
    ("chat_media", "id", {"unique": True}),
    ("friendships", "key", {"unique": True}),

    # Social
    ("posts", "id", {"unique": True}),
    ("posts", "authorId", {}),
    ("post_likes", [("postId", 1), ("userId", 1)], {"unique": True}),
    ("post_saves", [("postId", 1), ("userId", 1)], {"unique": True}),
    ("comments", [("postId", 1), ("createdAt", -1)], {}),
    ("follows", [("followerId", 1), ("authorId", 1)], {"unique": True}),
    ("follows", "authorId", {}),
    ("interests", "userId", {"unique": True}),

    # Marketplace
    ("listings", "id", {"unique": True}),
    ("listings", [("status", 1), ("category", 1)], {}),
    ("listings", "sellerId", {}),
    ("market_favorites", [("listingId", 1), ("userId", 1)], {"unique": True}),
    ("market_favorites", "userId", {}),
    ("market_images", "id", {"unique": True}),
    ("market_threads", "id", {"unique": True}),
    ("market_threads", "buyerId", {}),
    ("market_threads", "sellerId", {}),
    ("market_messages", [("threadId", 1), ("createdAt", 1)], {}),
    ("orders", "buyerId", {}),

    # Ads
    ("campaigns", "id", {"unique": True}),
    ("campaigns", [("ownerId", 1), ("createdAt", -1)], {}),
    ("campaigns", "status", {}),

    # App store & admin
    ("store_apps", "id", {"unique": True}),
    ("app_connections", [("userId", 1), ("appId", 1)], {"unique": True}),
    ("admin_connections", [("userId", 1), ("connectorId", 1)], {"unique": True}),
    ("admin_documents", [("userId", 1), ("createdAt", -1)], {}),

    # Assistant IA
    ("ai_messages", [("userId", 1), ("sessionId", 1), ("createdAt", 1)], {}),
    ("ai_messages", "actions.id", {}),

    # Notifications
    ("notifications", [("userId", 1), ("createdAt", -1)], {}),
    ("notifications", [("userId", 1), ("read", 1)], {}),

    # Paiement QR
    ("payment_requests", "code", {"unique": True}),
    ("payment_requests", "payeeId", {}),

    # Découverte & contacts
    ("users", "emailHash", {"sparse": True}),
    ("users", "phoneHash", {"sparse": True}),
    ("contacts_list", [("ownerId", 1), ("contactId", 1)], {"unique": True}),
    ("contact_requests", [("toId", 1), ("status", 1)], {}),
    ("contact_requests", [("fromId", 1), ("toId", 1)], {}),
    ("blocks", [("blockerId", 1), ("blockedId", 1)], {"unique": True}),
    ("invites", "code", {"unique": True}),
    ("invites", "inviterId", {}),
    ("nearby_pings", "userId", {"unique": True}),
    ("nearby_pings", "expiresAt", {"expireAfterSeconds": 0}),  # purge auto des pings expirés

    # Notifications push Web
    ("push_subscriptions", "endpoint", {"unique": True}),
    ("push_subscriptions", "userId", {}),
]


async def ensure_indexes(db: AsyncIOMotorDatabase) -> int:
    created = 0
    for coll, keys, opts in _INDEXES:
        try:
            await db[coll].create_index(keys, **opts)
            created += 1
        except Exception as e:  # noqa: BLE001
            print(f"[indexes] échec index {coll}{keys}: {e}")
    return created
