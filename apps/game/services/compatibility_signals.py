"""
Signaux textuels — alignement émotionnel, complémentarité et tensions.
"""

# Les deux réponses contiennent des marqueurs positifs
POSITIVE_WORDS: list[str] = [
    "oui", "absolument", "totalement", "d accord", "daccord", "ok", "bien sur",
    "adore", "aime", "aimer", "love", "heureux", "heureuse", "content", "contente",
    "genial", "super", "top", "parfait", "magnifique", "merveilleux", "incroyable",
    "envie", "trop", "vraiment", "profondement", "passionne", "passionnee",
    "ensemble", "toujours", "souvent", "important", "essentiel", "priorite",
    "confiance", "soutien", "complicité", "complicite", "tendresse", "amour",
    "gratitude", "reconnaissant", "fiere", "fier", "satisfait", "epanoui",
]

# Au moins une réponse contient un marqueur négatif fort
NEGATIVE_WORDS: list[str] = [
    "non", "jamais", "pas du tout", "aucun", "aucune", "refuse", "impossible",
    "deteste", "horreur", "peur", "angoisse", "stress", "colere", "furieux",
    "triste", "mal", "souffre", "souffrir", "inacceptable", "insupportable",
    "fin", "rupture", "quitter", "separer", "divorce", "toxique", "manipulation",
    "mensonge", "trahison", "jaloux", "jalousie", "doute", "méfiant", "mefiant",
]

# Complémentarité saine (différence constructive)
COMPLEMENTARY_PAIRS: list[tuple[list[str], list[str], int]] = [
    (["introverti", "introvertie", "calme", "tranquille", "rester", "maison", "discret"], ["extraverti", "extravertie", "sortir", "fete", "soiree", "sociable", "foule"], 5),
    (["planifier", "organiser", "structure", "ordre", "liste", "agenda"], ["spontane", "improviser", "surprise", "derniere minute", "impulsif"], 5),
    (["matin", "leve tot", "lark"], ["soir", "couche tard", "nuit", "owl"], 3),
    (["parler", "verbaliser", "discuter"], ["ecrire", "message", "lettre", "texto"], 3),
    (["sport", "actif", "bouger"], ["repos", "relax", "detente", "canape"], 3),
    (["ville", "urbain", "citadin"], ["nature", "campagne", "calme"], 4),
    (["economiser", "epargner", "budget"], ["depenser", "profiter", "cadeau"], 3),
    (["leader", "decide", "initiative"], ["soutien", "suit", "accompagne"], 3),
    (["creatif", "artistique"], ["logique", "analytique", "rationnel"], 3),
    (["emotion", "sensible", "coeur"], ["raison", "tete", "reflechi"], 4),
]

# Tensions (opposition forte — malus)
TENSION_PAIRS: list[tuple[list[str], list[str], int]] = [
    (["mariage", "me marier", "epouser", "oui je veux", "fiancailles"], ["pas pret", "pas prête", "jamais", "non au mariage", "pas maintenant", "contre le mariage"], -14),
    (["enfants", "avoir des enfants", "bebe", "grossesse", "parent"], ["pas d enfants", "childfree", "jamais d enfants", "sans enfant"], -12),
    (["fidelite", "exclusive", "monogamie"], ["libre", "poly", "open", "libertin"], -11),
    (["religion", "foi", "pratiquant", "eglise"], ["athe", "agnostique", "sans religion"], -8),
    (["ville", "urbain", "metropole", "paris"], ["campagne", "village", "isole", "loin"], -6),
    (["demenager", "expat", "partir loin"], ["rester", "racines", "ne pas bouger"], -7),
    (["achat", "credit", "immobilier"], ["location", "pas d achat", "mobile"], -5),
    (["chien", "chien"], ["chat", "deteste chien", "allergie chien"], -4),
    (["fumer", "cigarette"], ["non fumeur", "anti tabac"], -6),
    (["alcool", "apero", "soiree alcool"], ["sobre", "sans alcool", "alcool zero"], -5),
    (["temps ensemble", "toujours ensemble"], ["beaucoup d espace", "besoin seul", "independance totale"], -6),
    (["controle", "jaloux", "jalousie"], ["confiance totale", "liberte totale", "sans limite"], -5),
]

# Bonus si les deux partagent un ton positif (indépendant des thèmes)
POSITIVE_ALIGNMENT_BONUS = 6
# Malus si polarité opposée forte
POLARITY_CONFLICT_MALUS = -8
# Bonus modéré si même polarité négative (compréhension mutuelle des difficultés)
SHARED_NEGATIVE_BONUS = 3
