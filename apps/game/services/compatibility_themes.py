"""
Lexique thématique — matching déterministe à grande échelle (FR + variantes courantes).
Chaque thème : (id, mots-clés normalisés sans accent, bonus si présent des deux côtés).
"""

# fmt: off
THEME_RULES: list[tuple[str, list[str], int]] = [
    # --- Aventure & lifestyle ---
    ("travel", [
        "voyage", "voyager", "voyages", "monde", "aventure", "decouvrir", "explorer",
        "road trip", "backpack", "destination", "vacances", "escapade", "nomade",
        "billet", "avion", "train", "croisiere", "safari", "randonnee",
    ], 12),
    ("food", [
        "cuisine", "restaurant", "manger", "repas", "gastronomie", "chef", "recette",
        "brunch", "vin", "café", "cafe", "diner", "petit dejeuner", "foodie",
    ], 8),
    ("sport", [
        "sport", "gym", "fitness", "course", "running", "musculation", "yoga", "pilates",
        "foot", "football", "basket", "natation", "velo", "ski", "surf", "tennis",
    ], 8),
    ("nature", [
        "nature", "foret", "montagne", "mer", "plage", "campagne", "jardin", "animaux",
        "randonnee", "camping", "eco", "ecologie", "plein air", "lac", "riviere",
    ], 9),
    ("culture", [
        "musee", "theatre", "theatre", "concert", "expo", "art", "cinema", "film",
        "lecture", "livre", "musique", "festival", "culture", "spectacle",
    ], 7),
    # --- Foyer & quotidien ---
    ("home", [
        "maison", "chez nous", "foyer", "cocon", "appart", "appartement", "domicile",
        "interieur", "deco", "decoration", "cuisine maison", "salon", "chambre",
    ], 8),
    ("family", [
        "famille", "enfants", "enfant", "parents", "futurs parents", "bebe", "bb",
        "maman", "papa", "fratrie", "belle famille", "grossesse", "adoption",
    ], 10),
    ("pets", [
        "chien", "chat", "animal", "compagnon", "poisson", "nac", "veterinaire",
    ], 6),
    ("work", [
        "travail", "boulot", "carriere", "bureau", "teletravail", "remote", "boss",
        "collegue", "pro", "profession", "entrepreneur", "startup", "mission",
    ], 7),
    ("money", [
        "argent", "budget", "epargne", "finance", "investir", "economie", "depense",
        "salaire", "loyer", "credit", "frugal", "depenser", "richesse",
    ], 8),
    # --- Relation ---
    ("romance", [
        "amour", "romantique", "romantisme", "câlin", "câlins", "calin", "tendresse",
        "passion", "bisou", "baiser", "coeur", "amoureux", "amoureuse", "flamme",
        "crush", "couple", "petit ami", "petite amie", "cheri", "chérie",
    ], 10),
    ("intimacy", [
        "intimite", "intime", "proximite", "confiance", "vulnerabilite", "nu",
        "desir", "sensuel", "tendre", "caresse", "câlin", "lit", "chambre",
    ], 9),
    ("communication", [
        "parler", "discussion", "communiquer", "dialogue", "ecouter", "ecoute",
        "echanger", "exprimer", "se confier", "conversation", "mot", "parole",
        "dispute", "conflit", "reconciliation", "excuse", "pardon",
    ], 9),
    ("trust", [
        "confiance", "loyaute", "loyal", "honnête", "honnete", "sincere", "transparence",
        "fidèle", "fidele", "jaloux", "jalousie", "trahison", "secret",
    ], 10),
    ("humor", [
        "rire", "humour", "humoristique", "drole", "blague", "mdr", "lol",
        "sourire", "comique", "autodérision", "taquin", "farce",
    ], 8),
    ("support", [
        "soutien", "epauler", "present", "presence", "aider", "aide", "reconfort",
        "consoler", "encourager", "protecteur", "protectrice", "solidarite",
    ], 9),
    # --- Valeurs & avenir ---
    ("values", [
        "valeur", "valeurs", "respect", "integrite", "ethique", "principe", "morale",
        "justice", "egalite", "liberte", "spiritualite", "religion", "foi",
    ], 10),
    ("future", [
        "futur", "avenir", "projets", "projet", "ensemble", "construire", "plan",
        "objectif", "ambition", "reve", "reves", "vision", "trajectoire",
    ], 9),
    ("marriage", [
        "mariage", "marier", "epouser", "fiancailles", "fiancé", "fiancee", "noces",
        "alliance", "union", "ceremonie", "marié", "mariee",
    ], 9),
    ("commitment", [
        "engagement", "engage", "serieux", "long terme", "exclusive", "exclusif",
        "couple officiel", "relation stable", "fidélité", "fidelite",
    ], 8),
    ("freedom", [
        "liberte", "espace", "independance", "autonomie", "solo", "seul", "seule",
        "temps pour moi", "sans etouffer", "air", "personnel",
    ], 6),
    # --- Personnalité & social ---
    ("introvert", [
        "introverti", "introvertie", "calme", "tranquille", "rester", "maison",
        "silence", "discret", "reserve", "introspection", "livre", "netflix",
    ], 5),
    ("extrovert", [
        "extraverti", "extravertie", "sortir", "fete", "soiree", "sociable", "foule",
        "amis", "festif", "bar", "club", "rencontre", "network",
    ], 5),
    ("social", [
        "amis", "copains", "soiree", "diner", "invites", "groupe", "communaute",
        "reseau", "social", "party", "apero",
    ], 6),
    ("alone_time", [
        "temps seul", "besoin d espace", "pause", "recharger", "batteries",
        "introspection", "meditation", "balade seul",
    ], 5),
    # --- Émotions ---
    ("joy", [
        "heureux", "heureuse", "joie", "bonheur", "épanoui", "epanoui", "positive",
        "optimiste", "radieux", "content", "fiere", "fier",
    ], 7),
    ("stress", [
        "stress", "stressé", "stresse", "anxieux", "anxiete", "angoisse", "peur",
        "inquiet", "pression", "burn out", "fatigue", "epuisement",
    ], 6),
    ("anger", [
        "colere", "énervé", "enerve", "frustre", "frustration", "rage", "agace",
        "conflit", "dispute", "crier", "silence punition",
    ], 5),
    ("sadness", [
        "triste", "tristesse", "pleurer", "melancolie", "manque", "nostalgie",
        "deprime", "bleu", "down",
    ], 5),
    # --- Thèmes de vie ---
    ("health", [
        "sante", "sport", "bien etre", "wellness", "mental", "therapie", "psy",
        "medecin", "sommeil", "dormir", "regime", "nutrition",
    ], 7),
    ("education", [
        "etudes", "ecole", "universite", "formation", "apprendre", "diplome",
        "cursus", "etudiant",
    ], 5),
    ("creativity", [
        "creatif", "creative", "art", "peindre", "ecrire", "musique", "photo",
        "diy", "bricolage", "projet creatif",
    ], 6),
    ("tech", [
        "tech", "technologie", "gaming", "jeux video", "ordinateur", "smartphone",
        "reseaux", "instagram", "tiktok", "ecran", "digital",
    ], 5),
    ("eco", [
        "ecolo", "environnement", "durable", "recyclage", "zero dechet", "planete",
        "climat", "vert",
    ], 6),
    ("politics", [
        "politique", "societe", "engagement civique", "vote", "cause", "activisme",
    ], 4),
    # --- Gary Chapman (préparation au mariage) ---
    ("love_language", [
        "langage de l'amour", "langages de l'amour", "paroles valorisantes",
        "service rendu", "services rendus", "cadeau", "cadeaux", "moment de qualite",
        "moments de qualite", "toucher", "toucher physique", "caresse", "câlin",
        "attention exclusive", "remercier", "compliment",
    ], 11),
    ("forgiveness", [
        "pardonner", "pardon", "grece", "grace", "reconciliation", "lâcher prise",
        "justice", "offenser", "offense", "blessure passee",
    ], 10),
    ("apology", [
        "excuse", "excuses", "desole", "regret", "responsabilite", "reparation",
        "demander pardon", "s'excuser", "reconnaître", "changer de comportement",
    ], 10),
    ("in_laws", [
        "belle famille", "beaux parents", "belle mere", "beau pere", "belle fille",
        "gendre", "parents", "famille d'origine", "beau parent",
    ], 9),
    ("listening", [
        "ecoute active", "ecouter", "reformuler", "resume", "resumer", "sans couper",
        "parole", "entendre", "comprendre l'autre",
    ], 9),
    # --- Couple spécifique ---
    ("quality_time", [
        "temps ensemble", "moment a deux", "date", "rendez vous", "rdv", "soiree",
        "week end", "escapade", "rituel", "tradition couple",
    ], 9),
    ("distance", [
        "distance", "longue distance", "ld", "pays", "expat", "depart", "absence",
        "manque", "fuseau", "visio", "appel", "message",
    ], 6),
    ("chores", [
        "taches", "menage", "vaisselle", "linge", "nettoyer", "ranger", "courses",
        "partage", "equitable", "corvee",
    ], 6),
    ("parenting", [
        "parent", "parentalite", "education enfant", "ecole enfant", "garde",
        "nounou", "creche", "allaitement", "couche",
    ], 8),
    ("sexuality", [
        "sexualite", "sexe", "libido", "desir", "consentement", "plaisir",
        "intimite physique", "poly", "monogamie",
    ], 7),
    ("faith", [
        "dieu", "priere", "eglise", "mosquee", "synagogue", "spirituel", "karma",
        "meditation", "zen", "bouddhisme", "islam", "christianisme",
    ], 6),
    ("ambition", [
        "ambition", "reussite", "carriere", "promotion", "objectif pro", "bosser",
        "hustle", "reussir", "gagner", "performance",
    ], 7),
    ("simplicity", [
        "simple", "minimaliste", "slow life", "calme", "peu", "suffisant",
        "modeste", "petit bonheur",
    ], 6),
    ("adventure_risk", [
        "risque", "audace", "ose", "extreme", "saut", "parachute", "danger",
        "aventure extrême", "spontane",
    ], 7),
    ("stability", [
        "stable", "stabilite", "securite", "routine", "previsible", "cadre",
        "ancrage", "patrimoine", "assurance",
    ], 7),
]
# fmt: on

THEME_LABELS: dict[str, str] = {
    "travel": "voyage et découverte",
    "food": "gastronomie et partage",
    "sport": "activité physique",
    "nature": "nature et plein air",
    "culture": "culture et loisirs",
    "home": "foyer et cocon",
    "family": "famille et parentalité",
    "pets": "animaux de compagnie",
    "work": "vie professionnelle",
    "money": "finances du couple",
    "romance": "romantisme",
    "intimacy": "intimité",
    "communication": "communication",
    "trust": "confiance",
    "humor": "humour",
    "support": "soutien mutuel",
    "values": "valeurs communes",
    "future": "projets d'avenir",
    "marriage": "mariage et engagement",
    "commitment": "engagement relationnel",
    "freedom": "liberté personnelle",
    "introvert": "temps calme",
    "extrovert": "vie sociale",
    "social": "entourage et amis",
    "alone_time": "besoin d'espace",
    "joy": "joie partagée",
    "stress": "stress et charge mentale",
    "anger": "gestion de la colère",
    "sadness": "tristesse",
    "health": "santé et bien-être",
    "education": "formation",
    "creativity": "créativité",
    "tech": "technologie",
    "eco": "écologie",
    "politics": "engagement sociétal",
    "quality_time": "moments à deux",
    "distance": "relation à distance",
    "chores": "organisation du quotidien",
    "parenting": "parentalité",
    "sexuality": "intimité et sexualité",
    "faith": "spiritualité",
    "ambition": "ambition",
    "simplicity": "simplicité volontaire",
    "adventure_risk": "goût du risque",
    "stability": "recherche de stabilité",
    "love_language": "langages de l'amour",
    "forgiveness": "pardon et réconciliation",
    "apology": "excuses sincères",
    "in_laws": "famille et belle-famille",
    "listening": "écoute active",
}

# Thèmes renforcés quand la question est dans une catégorie donnée
CATEGORY_THEME_BOOST: dict[str, list[str]] = {
    "romantic": ["romance", "love_language", "intimacy", "quality_time", "trust"],
    "funny": ["humor", "joy", "social", "quality_time"],
    "spicy": ["intimacy", "romance", "sexuality", "trust", "love_language"],
    "deep": ["trust", "communication", "values", "forgiveness", "faith", "apology"],
    "know_partner": ["communication", "in_laws", "family", "love_language", "listening"],
    "future": ["future", "marriage", "commitment", "family", "money", "home"],
    "habits": ["chores", "home", "communication", "listening", "apology", "quality_time"],
}
