"""Constantes et jeux de données statiques (portés fidèlement depuis route.js)."""
from __future__ import annotations

COLORS = [
    "linear-gradient(135deg,#4353F0,#6E7BF5)", "linear-gradient(135deg,#E2AA2B,#F0CE7E)",
    "linear-gradient(135deg,#3FB68B,#7BE0BE)", "linear-gradient(135deg,#9B5DE5,#C89BF5)",
    "linear-gradient(135deg,#F15BB5,#FBA3D8)", "linear-gradient(135deg,#00BBF9,#7ADBFF)",
    "linear-gradient(135deg,#EF476F,#FF8FA8)", "linear-gradient(135deg,#2C39C7,#4353F0)",
]

LEVELS = [
    {"min": 0, "name": "Connaissance", "emoji": "🌱"},
    {"min": 100, "name": "Ami·e", "emoji": "💫"},
    {"min": 300, "name": "Bon·ne ami·e", "emoji": "💛"},
    {"min": 700, "name": "Meilleur·e ami·e", "emoji": "🔥"},
    {"min": 1500, "name": "Âme sœur", "emoji": "👑"},
]

BOTS = [
    {"id": "bot-marie", "name": "Marie Laurent", "handle": "@marie", "color": COLORS[1], "verified": True},
    {"id": "bot-thomas", "name": "Thomas Bernard", "handle": "@thomas", "color": COLORS[2], "verified": False},
    {"id": "bot-lena", "name": "Léna Costa", "handle": "@lena", "color": COLORS[3], "verified": True},
    {"id": "bot-yanis", "name": "Yanis Moreau", "handle": "@yanis", "color": COLORS[4], "verified": False},
    {"id": "bot-sofia", "name": "Sofia Ricci", "handle": "@sofia", "color": COLORS[5], "verified": True},
]

BOT_REPLIES = [
    "Haha carrément 😄", "Trop bien ! 🔥", "Je te réponds direct ⚡", "On fait ça 👌",
    "Ça marche pour moi 💛", "Génial, à très vite !", "Oui !! 🎉", "Je note 📝", "Top idée ✨",
]

VIDS = [
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
]

# ---------------- Marketplace v2 : catégories (type Leboncoin) ----------------
MARKET_CATEGORIES = [
    {"id": "immobilier", "name": "Immobilier", "emoji": "🏠", "color": "#4353F0", "types": ["sale", "rent"],
     "subcats": ["Ventes immobilières", "Locations", "Colocations", "Bureaux & commerces", "Locations de vacances"],
     "fields": [
         {"key": "propertyType", "label": "Type de bien", "type": "select", "options": ["Appartement", "Maison", "Studio", "Loft", "Terrain", "Parking", "Autre"]},
         {"key": "surface", "label": "Surface", "type": "number", "unit": "m²"},
         {"key": "rooms", "label": "Pièces", "type": "number"},
         {"key": "bedrooms", "label": "Chambres", "type": "number"},
         {"key": "furnished", "label": "Meublé", "type": "bool"},
         {"key": "energyClass", "label": "DPE", "type": "select", "options": ["A", "B", "C", "D", "E", "F", "G"]},
     ]},
    {"id": "vehicules", "name": "Véhicules", "emoji": "🚗", "color": "#EF476F", "types": ["sale", "rent"],
     "subcats": ["Voitures", "Motos", "Caravaning", "Utilitaires", "Nautisme"],
     "fields": [
         {"key": "brand", "label": "Marque", "type": "text"},
         {"key": "model", "label": "Modèle", "type": "text"},
         {"key": "year", "label": "Année", "type": "number"},
         {"key": "mileage", "label": "Kilométrage", "type": "number", "unit": "km"},
         {"key": "fuel", "label": "Carburant", "type": "select", "options": ["Essence", "Diesel", "Électrique", "Hybride", "GPL"]},
         {"key": "gearbox", "label": "Boîte", "type": "select", "options": ["Manuelle", "Automatique"]},
     ]},
    {"id": "multimedia", "name": "Multimédia", "emoji": "📱", "color": "#00BBF9", "types": ["sale"],
     "subcats": ["Informatique", "Téléphonie", "Image & son", "Consoles & jeux vidéo", "Accessoires"],
     "fields": [{"key": "brand", "label": "Marque", "type": "text"}]},
    {"id": "maison", "name": "Maison & Jardin", "emoji": "🛋️", "color": "#3FB68B", "types": ["sale"],
     "subcats": ["Ameublement", "Électroménager", "Décoration", "Bricolage", "Jardin & plantes", "Vaisselle"],
     "fields": []},
    {"id": "mode", "name": "Mode", "emoji": "👗", "color": "#F15BB5", "types": ["sale"],
     "subcats": ["Vêtements", "Chaussures", "Accessoires & bagagerie", "Montres & bijoux", "Beauté"],
     "fields": [{"key": "size", "label": "Taille", "type": "text"}, {"key": "brand", "label": "Marque", "type": "text"}]},
    {"id": "loisirs", "name": "Loisirs", "emoji": "🎸", "color": "#9B5DE5", "types": ["sale"],
     "subcats": ["Vélos", "Sport & plein air", "Instruments de musique", "Livres", "Jeux & jouets", "Collection"],
     "fields": []},
    {"id": "famille", "name": "Famille", "emoji": "👶", "color": "#F97C4E", "types": ["sale"],
     "subcats": ["Équipement bébé", "Mobilier enfant", "Vêtements bébé"],
     "fields": []},
    {"id": "emploi", "name": "Emploi & Services", "emoji": "💼", "color": "#E2AA2B", "types": ["sale", "service"],
     "subcats": ["Offres d’emploi", "Services à la personne", "Cours particuliers", "Événements", "Artisans"],
     "fields": []},
]
CONDITIONS = ["Neuf", "Comme neuf", "Très bon état", "Bon état", "État correct"]

EU_CC = "fr,de,es,it,be,nl,pt,lu,at,ie,fi,se,dk,pl,cz,gr,ro,hu,sk,si,hr,bg,ee,lv,lt,cy,mt,ch,no"

MARKET_IMGS = {
    "apartment": "https://images.pexels.com/photos/2030037/pexels-photo-2030037.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "house": "https://images.pexels.com/photos/20296321/pexels-photo-20296321.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "car": "https://images.pexels.com/photos/14776589/pexels-photo-14776589.jpeg",
    "motorcycle": "https://images.unsplash.com/photo-1449426468159-d96dbf08f19f",
    "sofa": "https://images.pexels.com/photos/6758245/pexels-photo-6758245.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "smartphone": "https://images.pexels.com/photos/47261/pexels-photo-47261.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "laptop": "https://images.pexels.com/photos/8003992/pexels-photo-8003992.jpeg",
    "sneakers": "https://images.pexels.com/photos/1027130/pexels-photo-1027130.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "bicycle": "https://images.pexels.com/photos/37858364/pexels-photo-37858364.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "guitar": "https://images.pexels.com/photos/9057791/pexels-photo-9057791.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
}
CITIES = {
    "Paris": [48.8566, 2.3522], "Lyon": [45.7640, 4.8357], "Marseille": [43.2965, 5.3698],
    "Bordeaux": [44.8378, -0.5792], "Nantes": [47.2184, -1.5536], "Lille": [50.6292, 3.0573],
    "Toulouse": [43.6047, 1.4442], "Berlin": [52.5200, 13.4050], "Madrid": [40.4168, -3.7038], "Bruxelles": [50.8503, 4.3517],
}

# ---------------- Ads Manager v2 (type Google Ads) ----------------
ADS_CONFIG = {
    "types": [
        {"id": "search", "name": "Search", "emoji": "🔎", "color": "#4353F0", "desc": "Annonces textuelles sur les recherches par mots-clés.", "defaultBid": "cpc"},
        {"id": "display", "name": "Display", "emoji": "🖼️", "color": "#9B5DE5", "desc": "Bannières visuelles sur le réseau DIVARC.", "defaultBid": "cpm"},
        {"id": "video", "name": "Vidéo", "emoji": "🎬", "color": "#EF476F", "desc": "Spots vidéo dans le feed Social.", "defaultBid": "cpm"},
        {"id": "shopping", "name": "Shopping", "emoji": "🛍️", "color": "#3FB68B", "desc": "Fiches produit avec prix dans le Marketplace.", "defaultBid": "cpc"},
    ],
    "objectives": [
        {"id": "sales", "name": "Ventes", "emoji": "💰"}, {"id": "leads", "name": "Prospects", "emoji": "🎯"},
        {"id": "traffic", "name": "Trafic", "emoji": "🌐"}, {"id": "awareness", "name": "Notoriété", "emoji": "📣"},
        {"id": "app", "name": "Promotion d’app", "emoji": "📱"},
    ],
    "bidStrategies": [
        {"id": "cpc", "name": "CPC manuel", "desc": "Coût par clic"}, {"id": "cpm", "name": "CPM", "desc": "Coût pour 1000 impressions"},
        {"id": "maximize", "name": "Maximiser les clics", "desc": "Enchère automatique"}, {"id": "target_cpa", "name": "CPA cible", "desc": "Coût par acquisition visé"},
    ],
    "interests": ["Tech", "Mode", "Voyage", "Food", "Sport", "Musique", "Gaming", "Finance", "Immobilier", "Auto", "Beauté", "Éducation", "Écologie", "Famille"],
    "devices": ["Mobile", "Ordinateur", "Tablette"],
    "ageRanges": ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
    "genders": ["Tous", "Femmes", "Hommes"],
}

# ---------------- App Store : vraies apps du marché ----------------
APP_CAT_PERMS = {
    "Social": ["Profil", "Photos", "Contacts"],
    "Réseaux pro": ["Profil", "Contacts", "Expérience"],
    "Vidéo": ["Profil", "Historique"],
    "Messagerie": ["Profil", "Contacts"],
    "Streaming": ["Profil", "Paiement"],
    "Musique": ["Profil", "Paiement"],
    "Finance": ["Profil", "Identité", "Paiement"],
    "Mobilité": ["Profil", "Localisation", "Paiement"],
    "Shopping": ["Profil", "Adresse", "Paiement"],
    "Repas": ["Profil", "Localisation", "Paiement"],
    "Productivité": ["Profil", "Fichiers"],
    "Rencontre": ["Profil", "Photos", "Localisation"],
}
APP_CAT_DESC = {
    "Social": lambda n: f"Partage tes moments, tes stories et suis tes amis sur {n}.",
    "Réseaux pro": lambda n: f"Développe ton réseau professionnel et ta carrière avec {n}.",
    "Vidéo": lambda n: f"Regarde et diffuse des vidéos en direct sur {n}.",
    "Messagerie": lambda n: f"Discute en privé et en groupe, chiffré, sur {n}.",
    "Streaming": lambda n: f"Films & séries en illimité — reprends la lecture partout avec {n}.",
    "Musique": lambda n: f"Des millions de titres et playlists à écouter sur {n}.",
    "Finance": lambda n: f"Gère ton argent, tes paiements et tes cartes avec {n}.",
    "Mobilité": lambda n: f"Déplace-toi en un tap, payé depuis ton wallet, avec {n}.",
    "Shopping": lambda n: f"Achète tout, livré rapidement, paiement wallet sur {n}.",
    "Repas": lambda n: f"Fais-toi livrer tes plats préférés avec {n}.",
    "Productivité": lambda n: f"Organise ton travail et tes fichiers avec {n}.",
    "Rencontre": lambda n: f"Fais de nouvelles rencontres près de chez toi sur {n}.",
}
# [id, name, simpleicons slug, brand color, category, featured]
STORE_RAW = [
    ["instagram", "Instagram", "instagram", "#E4405F", "Social", True],
    ["tiktok", "TikTok", "tiktok", "#010101", "Social", True],
    ["facebook", "Facebook", "facebook", "#0866FF", "Social", False],
    ["x", "X", "x", "#000000", "Social", False],
    ["snapchat", "Snapchat", "snapchat", "#0FADFF", "Social", False],
    ["pinterest", "Pinterest", "pinterest", "#BD081C", "Social", False],
    ["reddit", "Reddit", "reddit", "#FF4500", "Social", False],
    ["threads", "Threads", "threads", "#000000", "Social", False],
    ["linkedin", "LinkedIn", "linkedin", "#0A66C2", "Réseaux pro", True],
    ["youtube", "YouTube", "youtube", "#FF0000", "Vidéo", True],
    ["twitch", "Twitch", "twitch", "#9146FF", "Vidéo", False],
    ["whatsapp", "WhatsApp", "whatsapp", "#25D366", "Messagerie", True],
    ["telegram", "Telegram", "telegram", "#26A5E4", "Messagerie", False],
    ["messenger", "Messenger", "messenger", "#00B2FF", "Messagerie", False],
    ["signal", "Signal", "signal", "#3A76F0", "Messagerie", False],
    ["discord", "Discord", "discord", "#5865F2", "Messagerie", False],
    ["netflix", "Netflix", "netflix", "#E50914", "Streaming", True],
    ["primevideo", "Prime Video", "primevideo", "#1F2E5E", "Streaming", False],
    ["disneyplus", "Disney+", "disneyplus", "#113CCF", "Streaming", False],
    ["spotify", "Spotify", "spotify", "#1DB954", "Musique", True],
    ["deezer", "Deezer", "deezer", "#A238FF", "Musique", False],
    ["paypal", "PayPal", "paypal", "#003087", "Finance", False],
    ["revolut", "Revolut", "revolut", "#191C1F", "Finance", False],
    ["coinbase", "Coinbase", "coinbase", "#0052FF", "Finance", False],
    ["uber", "Uber", "uber", "#000000", "Mobilité", True],
    ["blablacar", "BlaBlaCar", "blablacar", "#00AFF5", "Mobilité", False],
    ["amazon", "Amazon", "amazon", "#FF9900", "Shopping", False],
    ["vinted", "Vinted", "vinted", "#09B1BA", "Shopping", False],
    ["zalando", "Zalando", "zalando", "#FF6900", "Shopping", False],
    ["ubereats", "Uber Eats", "ubereats", "#06C167", "Repas", False],
    ["deliveroo", "Deliveroo", "deliveroo", "#00CCBC", "Repas", False],
    ["notion", "Notion", "notion", "#000000", "Productivité", False],
    ["slack", "Slack", "slack", "#4A154B", "Productivité", False],
    ["zoom", "Zoom", "zoom", "#0B5CFF", "Productivité", False],
    ["dropbox", "Dropbox", "dropbox", "#0061FF", "Productivité", False],
    ["tinder", "Tinder", "tinder", "#FF6B6B", "Rencontre", False],
    ["bumble", "Bumble", "bumble", "#FFC629", "Rencontre", False],
]


def store_apps() -> list[dict]:
    apps = []
    for _id, name, slug, color, cat, featured in STORE_RAW:
        desc_fn = APP_CAT_DESC.get(cat) or (lambda n: f"Connecte {n} à ton identité DIVARC.")
        apps.append({
            "id": _id, "name": name, "slug": slug, "color": color, "cat": cat, "featured": bool(featured),
            "logo": f"https://cdn.simpleicons.org/{slug}/FFFFFF", "emoji": "📱",
            "desc": desc_fn(name), "perms": APP_CAT_PERMS.get(cat) or ["Profil"],
        })
    return apps


STORE_APPS = store_apps()

# ---------------- Hub administratif & santé : connecteurs État (mock eIDAS) ----------------
ADMIN_CONN = [
    {"id": "impots", "name": "Impôts.gouv", "cat": "Fiscalité", "emoji": "🧾", "color": "#4353F0", "desc": "Ton avis d’imposition, tes acomptes et ton taux de prélèvement à la source.", "scopes": ["Identité", "Revenus fiscaux"], "sensitive": False},
    {"id": "ameli", "name": "Ameli · Assurance Maladie", "cat": "Santé", "emoji": "⚕️", "color": "#3FB68B", "desc": "Tes remboursements, ta carte Vitale et ton médecin traitant.", "scopes": ["Identité", "Données de santé"], "sensitive": True},
    {"id": "caf", "name": "CAF · Allocations", "cat": "Social", "emoji": "👨‍👩‍👧", "color": "#E2AA2B", "desc": "Tes droits, quotient familial et versements d’aides.", "scopes": ["Identité", "Situation familiale"], "sensitive": False},
    {"id": "ants", "name": "ANTS · Titres", "cat": "Identité", "emoji": "🪪", "color": "#6E7BF5", "desc": "Permis de conduire, carte grise, points et démarches.", "scopes": ["Identité", "Titres"], "sensitive": False},
    {"id": "assurance", "name": "Retraite · Info", "cat": "Retraite", "emoji": "🏛️", "color": "#5B5A50", "desc": "Relevé de carrière et estimation de ta future pension.", "scopes": ["Identité", "Carrière"], "sensitive": False},
]
ADMIN_DATA = {
    "impots": [
        {"label": "Revenu fiscal de référence", "value": "38 420 €"},
        {"label": "Taux de prélèvement", "value": "9,3 %"},
        {"label": "Prochain acompte", "value": "298 € · 15 juil."},
        {"label": "Avis 2024", "value": "Disponible"},
    ],
    "ameli": [
        {"label": "Remboursements en attente", "value": "2 · 47,80 €"},
        {"label": "Médecin traitant", "value": "Dr. Lefèvre"},
        {"label": "Carte Vitale", "value": "À jour"},
        {"label": "Plafond mutuelle", "value": "82 %"},
    ],
    "caf": [
        {"label": "Quotient familial", "value": "1 240"},
        {"label": "Aides actives", "value": "APL · 214 €/mois"},
        {"label": "Prochain versement", "value": "5 du mois"},
        {"label": "Situation", "value": "À jour"},
    ],
    "ants": [
        {"label": "Permis", "value": "Valide · 12 pts"},
        {"label": "Carte grise", "value": "AB-123-CD"},
        {"label": "Démarche en cours", "value": "Aucune"},
    ],
    "assurance": [
        {"label": "Trimestres validés", "value": "68"},
        {"label": "Pension estimée", "value": "1 640 €/mois"},
        {"label": "Départ estimé", "value": "2049"},
    ],
}
