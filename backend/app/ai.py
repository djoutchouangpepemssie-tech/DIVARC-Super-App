"""Assistant IA « DIVA » — prompt, normalisation d'actions, appel Anthropic (porté depuis route.js)."""
from __future__ import annotations

import json
import re
from typing import Any

from anthropic import Anthropic

from .config import settings
from .helpers import eur, uid


def ai_system_prompt(ctx: dict) -> str:
    contacts = ", ".join(f"{c['name']} ({c['handle']})" for c in ctx["contacts"]) or "aucun"
    return f"""Tu es DIVA, le copilote IA de DIVARC, la super-app européenne (RGPD, respect de la vie privée).
Tu tutoies l'utilisateur, tu réponds en FRANÇAIS, de façon chaleureuse, concise et utile.

CONTEXTE UTILISATEUR (ne le répète pas tel quel) :
- Prénom : {ctx['name']}
- Solde du wallet : {ctx['balanceCents'] / 100:.2f} €
- Contacts disponibles : {contacts}

TU PEUX PROPOSER DES ACTIONS que l'utilisateur confirmera lui-même (slide-to-confirm). Tu n'exécutes JAMAIS toi-même.
Types d'actions autorisés et forme du "payload" :
- "send_money" : envoyer de l'argent. payload = {{ "toName": string (un des contacts), "amountCents": number (en centimes), "message": string optionnel }}. risk = "high".
- "create_listing" : déposer une annonce Marketplace. payload = {{ "title": string, "priceCents": number, "category": "immobilier"|"vehicules"|"multimedia"|"maison"|"mode"|"loisirs"|"famille"|"emploi", "description": string, "city": string }}. risk = "medium".
- "launch_ad" : lancer une campagne pub. payload = {{ "name": string, "type": "search"|"display"|"video"|"shopping", "objective": "sales"|"leads"|"traffic"|"awareness"|"app", "budgetCents": number }}. risk = "high".
- "navigate" : ouvrir un écran. payload = {{ "tab": "hub"|"wallet"|"messages"|"market"|"ads"|"store"|"admin"|"social"|"discover" }}. risk = "low".

RÈGLES :
- Proposer une action est TOUJOURS SÛR : l'utilisateur doit lui-même la confirmer par un glissement (slide-to-confirm) avant toute exécution. Tu ne déclenches donc jamais rien directement — n'hésite donc JAMAIS à proposer une action quand l'intention est claire.
- NE DEMANDE JAMAIS de confirmation verbale (interdit : « Confirmes-tu ? », « Voulez-vous que… ? »). Le GLISSEMENT est la confirmation. Propose directement l'action.
- Remplis TOUJOURS le payload COMPLÈTEMENT à partir du message : montant en centimes, destinataire (toName), titre, prix, ville, budget, etc. Ne laisse JAMAIS un champ vide s'il est déduisible du message.
- Quand l'utilisateur demande d'envoyer de l'argent, vendre un objet, lancer une pub ou ouvrir un écran : PROPOSE l'action correspondante (ne refuse pas, ne fais pas la morale).
- Pour send_money : amountCents en centimes (20 € => 2000), toName = le prénom/nom donné. Si aucun destinataire n'est donné, demande UNE précision (actions vides).
- Ne propose jamais plus de 2 actions.
- Si l'intention n'est vraiment pas claire, pose UNE question courte (actions vides).

EXEMPLES (montrent le format attendu) :
Utilisateur : "Envoie 20 € à Marie"
Toi : {{"assistant_message":"C'est prêt ! Fais glisser pour envoyer 20 € à Marie.","actions":[{{"id":"a1","type":"send_money","title":"Envoyer 20 € à Marie","summary":"Virement instantané depuis ton wallet.","payload":{{"toName":"Marie","amountCents":2000}},"risk":"high"}}]}}
Utilisateur : "Je veux vendre mon vélo 150 € à Lyon"
Toi : {{"assistant_message":"Super, voici ton annonce prête à publier.","actions":[{{"id":"a1","type":"create_listing","title":"Vendre : Vélo","summary":"Annonce Marketplace à 150 €.","payload":{{"title":"Vélo","priceCents":15000,"category":"loisirs","description":"Vélo en bon état.","city":"Lyon"}},"risk":"medium"}}]}}
Utilisateur : "Lance une campagne de notoriété à 50 €"
Toi : {{"assistant_message":"Voici ta campagne, prête à lancer.","actions":[{{"id":"a1","type":"launch_ad","title":"Campagne Notoriété","summary":"Budget 50 €, réseau DIVARC.","payload":{{"name":"Campagne Notoriété","type":"display","objective":"awareness","budgetCents":5000}},"risk":"high"}}]}}
Utilisateur : "Ouvre mon wallet"
Toi : {{"assistant_message":"J'ouvre ton wallet.","actions":[{{"id":"a1","type":"navigate","title":"Ouvrir le Wallet","summary":"","payload":{{"tab":"wallet"}},"risk":"low"}}]}}

RÉPONDS STRICTEMENT EN JSON VALIDE, SANS MARKDOWN, au format exact :
{{"assistant_message": string, "actions": [{{"id": string, "type": string, "title": string, "summary": string, "payload": object, "risk": "low"|"medium"|"high"}}]}}"""


def ai_canon_type(t: Any) -> dict:
    s = str(t or "").lower()
    if re.search(r"(navigate|navigation|open|ouvrir|go[_ ]?to|afficher|show|screen|voir)", s):
        m = re.search(r"(wallet|marketplace|market|messages?|messagerie|ads?|pub|store|admin|social|hub|discover|découvrir|accueil|profil)", s)
        tab = None
        if m:
            w = m.group(1)
            if w.startswith("message") or w == "messagerie":
                tab = "messages"
            elif w == "marketplace":
                tab = "market"
            elif w == "pub":
                tab = "ads"
            elif w == "découvrir":
                tab = "discover"
            elif w == "accueil":
                tab = "hub"
            else:
                tab = w
        return {"c": "navigate", "tab": tab}
    if re.search(r"(send|transfer|virement|envoi|envoyer|pay|payment|paiement|money|argent)", s):
        return {"c": "send_money", "tab": None}
    if re.search(r"(ad|advert|campaign|campagne|pub|marketing|sponsor)", s):
        return {"c": "launch_ad", "tab": None}
    if re.search(r"(listing|sell|vendre|vente|annonce|market|classified|item)", s):
        return {"c": "create_listing", "tab": None}
    return {"c": None, "tab": None}


def ai_default_title(t: str, p: dict) -> str:
    if t == "send_money":
        return f"Envoyer {eur(p.get('amountCents'))} à {p.get('toName') or 'un contact'}"
    if t == "create_listing":
        return f"Vendre : {p.get('title') or 'article'}"
    if t == "launch_ad":
        return f"Campagne : {p.get('name') or 'pub'}"
    if t == "navigate":
        return "Ouvrir l’écran"
    return "Action"


AD_TYPES = ["search", "display", "video", "shopping"]
AD_OBJECTIVES = ["sales", "leads", "traffic", "awareness", "app"]
_SKIP = {"type", "action_type", "action", "payload", "parameters", "params", "args", "id", "title", "summary", "risk"}


def _to_cents(v: Any) -> int | None:
    if v is None or v == "":
        return None
    cleaned = re.sub(r"[^0-9.,-]", "", str(v)).replace(",", ".")
    try:
        return round(float(cleaned) * 100)
    except ValueError:
        return None


def ai_normalize_action(a: dict, tab_hint: str | None = None) -> dict:
    pl = {}
    for src_key in ("payload", "parameters", "params", "args"):
        if isinstance(a.get(src_key), dict):
            pl = a[src_key]
            break

    def pick(*keys):
        for k in keys:
            if pl.get(k) not in (None, ""):
                return pl.get(k)
            if a.get(k) not in (None, "") and k not in _SKIP:
                return a.get(k)
        return None

    canon = ai_canon_type(a.get("type") or a.get("action_type") or a.get("action"))
    t = canon["c"]
    payload: dict = {}
    if t == "send_money":
        cents = pl.get("amountCents") if pl.get("amountCents") is not None else (a.get("amountCents") if a.get("amountCents") is not None else _to_cents(pick("amount", "montant", "amountEur", "value", "sum")))
        payload = {"toName": pick("toName", "recipient", "to", "contact", "destinataire", "beneficiaire", "name", "friend"),
                   "amountCents": cents, "message": pick("message", "note", "memo") or ""}
    elif t == "create_listing":
        price = pl.get("priceCents") if pl.get("priceCents") is not None else (a.get("priceCents") if a.get("priceCents") is not None else _to_cents(pick("price", "prix", "amount", "montant")))
        payload = {"title": pick("title", "titre", "item", "objet", "name", "produit", "product"),
                   "priceCents": price, "category": pick("category", "categorie"),
                   "description": pick("description", "desc") or "", "city": pick("city", "ville", "location", "lieu") or ""}
    elif t == "launch_ad":
        camp = pl.get("type") or pl.get("campaignType") or pl.get("campaign_type") or a.get("campaignType") or a.get("adType") or pick("adType", "kind")
        obj = pick("objective", "objectif", "goal")
        camp = str(camp or "").lower()
        obj = str(obj or "").lower()
        if camp in AD_OBJECTIVES and obj not in AD_OBJECTIVES:
            obj = camp
            camp = ""
        if camp not in AD_TYPES:
            camp = "display"
        if obj not in AD_OBJECTIVES:
            obj = "awareness"
        budget = pl.get("budgetCents") if pl.get("budgetCents") is not None else (a.get("budgetCents") if a.get("budgetCents") is not None else _to_cents(pick("budget", "budgetEur", "amount", "montant")))
        payload = {"name": pick("name", "nom", "title", "campaignName", "campaign_name") or "Campagne",
                   "type": camp, "objective": obj, "budgetCents": budget}
    elif t == "navigate":
        payload = {"tab": pick("tab", "screen", "page", "destination", "route") or tab_hint or canon["tab"] or "hub"}

    payload = {k: v for k, v in payload.items() if v is not None}
    return {"id": a.get("id") or uid(), "type": t, "title": a.get("title") or ai_default_title(t, payload),
            "summary": a.get("summary") or "", "payload": payload,
            "risk": a.get("risk") or ("low" if t == "navigate" else "medium" if t == "create_listing" else "high")}


def ai_parse_json(raw: str) -> dict:
    if not raw:
        return {"assistant_message": "", "actions": [], "_json": False}
    s = str(raw).strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
    s = re.sub(r"\s*```$", "", s, flags=re.I).strip()
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        s = s[start:end + 1]
    try:
        p = json.loads(s)
        raw_actions = p.get("actions") if isinstance(p.get("actions"), list) else []
        actions = []
        for a in raw_actions:
            hint = ai_canon_type(a.get("type") or a.get("action_type") or a.get("action"))["tab"]
            na = ai_normalize_action(a, hint)
            if na["type"] in ("send_money", "create_listing", "launch_ad", "navigate"):
                actions.append(na)
        actions = actions[:3]
        return {"assistant_message": p.get("assistant_message") or p.get("message") or "", "actions": actions,
                "_json": isinstance(p.get("assistant_message"), str) or isinstance(p.get("actions"), list)}
    except (json.JSONDecodeError, AttributeError):
        return {"assistant_message": str(raw)[:500], "actions": [], "_json": False}


async def ai_build_context(db, me: dict) -> dict:
    wallet = await db.wallets.find_one({"userId": me["id"]})
    contacts = await db.users.find({"id": {"$ne": me["id"]}}, {"_id": 0, "name": 1, "handle": 1}).limit(12).to_list(length=12)
    return {"name": me.get("name") or "toi", "balanceCents": (wallet or {}).get("balanceCents") or 0, "contacts": contacts}


def ai_build_messages(history: list[dict], user_text: str) -> list[dict]:
    """Alternance stricte user/assistant, premier message = user (contraintes API Anthropic)."""
    msgs: list[dict] = []
    for m in history:
        role = "assistant" if m.get("role") == "assistant" else "user"
        content = str(m.get("content") or "")
        if not content:
            continue
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n" + content
        else:
            msgs.append({"role": role, "content": content})
    if msgs and msgs[-1]["role"] == "user":
        msgs[-1]["content"] += "\n" + user_text
    else:
        msgs.append({"role": "user", "content": user_text})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def ai_complete(system_prompt: str, messages: list[dict]) -> str:
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=settings.AI_MODEL, max_tokens=1200, temperature=0,
        system=system_prompt, messages=messages,
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
