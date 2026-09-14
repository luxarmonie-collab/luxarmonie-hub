"""
Configuration des pays pour Luxarmonie Pricing Manager
- Terminaisons psychologiques (FIXES)
- TVA par défaut
- Taux de change par défaut (modifiables via l'interface)
"""

# Terminaisons par type (NE PAS MODIFIER - règles culturelles)
ENDINGS = {
    "99": lambda p: float(int(p)) + 0.99,           # France, USA, UK, etc.
    "95": lambda p: float(int(p)) + 0.95,           # Allemagne, Autriche, Suisse
    "00": lambda p: float(round(p)),                 # High-context: Brésil, Italie, etc.
    "9_int": lambda p: float(int(p) - (int(p) % 10) + 9) if int(p) % 10 != 9 else float(int(p)),  # Moyen-Orient
    "000": lambda p: float(round(p / 1000) * 1000),  # Grandes devises: Chili, Colombie
    "990": lambda p: float((int(p) // 1000) * 1000 + 990) if p >= 10000 else float((int(p) // 100) * 100 + 90),  # Hongrie, Tchéquie
    "kr": lambda p: float(round(p / 5) * 5),         # Scandinave: DKK, SEK
}

# Configuration complète par pays
COUNTRIES = {
    # === ZONE EURO AVEC TVA ===
    "France": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.19,
        "adjustment": "vat",  # -12% puis +TVA
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Allemagne": {
        "currency": "EUR",
        "ending": "95",
        "vat": 0.19,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Luxembourg": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.17,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Autriche": {
        "currency": "EUR",
        "ending": "95",
        "vat": 0.20,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Belgique": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Espagne": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Italie": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Pays-Bas": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "ESTONIE": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.24,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Grèce": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.24,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Irlande": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.24,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Portugal": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.24,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Croatie": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.25,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Finlande": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.25,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    
    # === EUROPE HORS EURO ===
    "Danemark": {
        "currency": "DKK",
        "ending": "kr",
        "vat": 0.25,
        "adjustment": "vat",
        "exchange_rate": 7.60,
        "culture": "low-context"
    },
    "Suède": {
        "currency": "SEK",
        "ending": "kr",
        "vat": 0.25,
        "adjustment": "vat",
        "exchange_rate": 11.50,
        "culture": "low-context"
    },
    "Norvège": {
        "currency": "NOK",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 12.00,
        "culture": "low-context"
    },
    "Hongrie": {
        "currency": "HUF",
        "ending": "990",
        "vat": 0.27,
        "adjustment": "vat",
        "exchange_rate": 405,
        "culture": "low-context"
    },
    "Pologne": {
        "currency": "PLN",
        "ending": "99",
        "vat": 0.23,
        "adjustment": "vat",
        "exchange_rate": 4.50,
        "culture": "low-context"
    },
    "République tchèque": {
        "currency": "CZK",
        "ending": "990",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 25.50,
        "culture": "low-context"
    },
    "Serbie": {
        "currency": "RSD",
        "ending": "990",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 120,
        "culture": "low-context"
    },
    "Bulgarie": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.20,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Roumanie": {
        "currency": "EUR",
        "ending": "99",
        "vat": 0.19,
        "adjustment": "vat",
        "exchange_rate": 1,
        "culture": "low-context"
    },
    "Suisse": {
        "currency": "CHF",
        "ending": "95",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 0.93,
        "culture": "low-context"
    },
    "UK": {
        "currency": "GBP",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 0.88,
        "culture": "low-context"
    },
    
    # === AMÉRIQUE DU NORD ===
    "USA": {
        "currency": "USD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.20,
        "culture": "low-context"
    },
    "Canada": {
        "currency": "CAD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.60,
        "culture": "low-context"
    },
    "Mexique": {
        "currency": "MXN",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 22.00,
        "culture": "low-context"
    },
    
    # === AMÉRIQUE DU SUD ===
    "Brésil": {
        "currency": "BRL",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 6.45,
        "culture": "high-context"
    },
    "Argentine": {
        "currency": "ARS",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1375,
        "culture": "high-context"
    },
    "Chili": {
        "currency": "CLP",
        "ending": "000",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1050,
        "culture": "low-context"
    },
    "Colombie": {
        "currency": "COP",
        "ending": "000",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4780,
        "culture": "low-context"
    },
    "Paraguay": {
        "currency": "PYG",
        "ending": "000",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 8800,
        "culture": "low-context"
    },
    "Pérou": {
        "currency": "PEN",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.35,
        "culture": "low-context"
    },
    "Bolivie": {
        "currency": "BOB",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 8.00,
        "culture": "low-context"
    },
    "Équateur": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Uruguay": {
        "currency": "UYU",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 48.00,
        "culture": "high-context"
    },
    "Costa Rica": {
        "currency": "CRC",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 590,
        "culture": "low-context"
    },
    "Guatemala": {
        "currency": "GTQ",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 8.95,
        "culture": "low-context"
    },
    "Honduras": {
        "currency": "HNL",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 29.00,
        "culture": "low-context"
    },
    "République dominicaine": {
        "currency": "DOP",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 70.00,
        "culture": "low-context"
    },
    "Panama": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Salvador": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    
    # === MOYEN-ORIENT ===
    "Arabie Saoudite": {
        "currency": "SAR",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.50,
        "culture": "high-context"
    },
    "Émirats Arabes Unis": {
        "currency": "AED",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.30,
        "culture": "high-context"
    },
    "Qatar": {
        "currency": "QAR",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.30,
        "culture": "high-context"
    },
    "Bahreïn": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Koweït": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Oman": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Jordanie": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Liban": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Israël": {
        "currency": "ILS",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.20,
        "culture": "low-context"
    },
    
    # === ASIE-PACIFIQUE ===
    "Japon": {
        "currency": "JPY",
        "ending": "000",
        "vat": 0.10,
        "adjustment": "vat",
        "exchange_rate": 186.50,
        "culture": "high-context"
    },
    "Corée du Sud": {
        "currency": "KRW",
        "ending": "000",
        "vat": 0.10,
        "adjustment": "vat",
        "exchange_rate": 1737.00,
        "culture": "high-context"
    },
    "Pakistan": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Australie": {
        "currency": "AUD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.80,
        "culture": "low-context"
    },
    "Nouvelle Zélande": {
        "currency": "NZD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.92,
        "culture": "low-context"
    },
    "Honk Hong": {
        "currency": "HKD",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 9.00,
        "culture": "high-context"
    },
    "SINGAPOUR": {
        "currency": "SGD",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.52,
        "culture": "high-context"
    },
    "Malaisie": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
    "Turquie": {
        "currency": "TRY",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 46.50,
        "culture": "low-context"
    },

    # === AFRIQUE ===
    "Afrique du Sud": {
        "currency": "ZAR",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 22.00,
        "culture": "high-context"
    },
}

# Devises qui n'ont pas de décimales
NO_DECIMAL_CURRENCIES = [
    "HUF", "CZK", "RSD", "CLP", "COP", "PYG",
    "SAR", "QAR", "AED", "DKK", "SEK", "NOK",
    "HKD", "CRC", "UYU", "DOP", "JPY", "KRW"
]

def get_country_config(country_name: str) -> dict:
    """Récupère la config d'un pays"""
    return COUNTRIES.get(country_name, None)

def get_ending_function(ending_type: str):
    """Récupère la fonction d'arrondi pour un type de terminaison"""
    return ENDINGS.get(ending_type, ENDINGS["99"])

def format_price(price: float, currency: str) -> str:
    """Formate le prix selon la devise"""
    if currency in NO_DECIMAL_CURRENCIES:
        return str(int(price))
    return f"{price:.2f}"

def get_all_countries() -> list:
    """Liste tous les pays disponibles"""
    return list(COUNTRIES.keys())


# ═══════════════════════════════════════════════════════════════════════════
# RÉSOLUTION STRICTE DES NOMS DE PAYS + TERMINAISONS — SOURCE UNIQUE
# Leo, 2026-09-14. Tickets Paul bus #5338 / #5364 / #5391 / #5419.
#
# Deux défauts structurels réparés ici, tous deux de la famille
# « fallback silencieux qui produit un résultat d'apparence valide » :
#
# 1) NOM DE PAYS INCONNU → devise EUR + taux 1.0
#    `COUNTRIES.get(country, {})` suivi de `.get("currency", "EUR")` rendait
#    un preview crédible pour un pays qui n'existe pas. Mesuré par Paul le
#    10/09 : countries=['Nouvelle-Zélande'] (avec trait d'union — le vrai nom
#    est sans) renvoyait EUR + prix de base BRUT ; un apply aurait écrit cette
#    valeur dans la price list EUR partagée par JO/KW/LB/MY/NZ/OM/PA/SV/TR/EC.
#    Même famille de dégât que le countries=['all'] sur ZA/AR/TR d'août.
#    => resolve_country() tolère accents/casse/espaces mais REFUSE l'inconnu,
#       en proposant les noms proches (pas de devinette silencieuse).
#
# 2) TABLE D'ARRONDI DUPLIQUÉE 3× ET DÉRIVÉE
#    `ending` vit ici, mais routers/fix_price.py, routers/pricing.py et
#    routers/csv_processor.py portaient chacun leur propre table
#    country -> fonction d'arrondi. Les trois avaient divergé de celle-ci.
#    Écarts mesurés le 14/09 sur les 62 pays configurés :
#      - fix_price : 10 pays ABSENTS de sa table donc arrondis en .99 par
#        défaut, dont Japon (JPY, doit finir en 000) et Corée du Sud (KRW,
#        000). C'est exactement le « JP 22 937,99 JPY » remonté par Paul —
#        des centimes sur une devise sans décimale. Aussi Koweït/Oman/
#        Jordanie/Liban/Pakistan (doivent finir en 00) et Bulgarie/Roumanie/
#        République dominicaine.
#      - fix_price : Afrique du Sud en 00 alors qu'ici c'est 9_int.
#      - fix_price : clé morte 'Hong Kong' (le nom réel côté Shopify est
#        'Honk Hong', faute incluse).
#      - pricing.py : pire encore, son fallback faisait float(ending), donc
#        "9_int" et "kr" levaient (→ .99 par défaut), "000" devenait 0.0
#        (simple floor au lieu d'arrondir au millier : Chili, Colombie) et
#        "990" devenait 9.90 (Hongrie/Tchéquie/Serbie finissaient en X,90 au
#        lieu de X990).
#    => apply_ending() ci-dessous est le SEUL chemin. Les trois routers
#       l'appellent. Ajouter un marché = éditer COUNTRIES, rien d'autre.
#
# Les implémentations retenues sont les plus défensives des quatre variantes
# qui coexistaient (branche < 1000 de round_990, garde max(...,1) de round_000).
# ═══════════════════════════════════════════════════════════════════════════

import math as _math
import re as _re
import unicodedata as _unicodedata


class UnknownCountryError(ValueError):
    """Nom de pays absent de COUNTRIES. Porte les suggestions proches."""

    def __init__(self, name: str, suggestions: list):
        self.name = name
        self.suggestions = suggestions
        msg = f"Pays inconnu : '{name}'."
        if suggestions:
            msg += " Vouliez-vous dire : " + ", ".join(f"'{s}'" for s in suggestions) + " ?"
        super().__init__(msg)


def _fold(name: str) -> str:
    """Casse + accents + ponctuation neutralisés, pour comparer des noms."""
    nf = _unicodedata.normalize("NFKD", str(name))
    ascii_only = "".join(c for c in nf if not _unicodedata.combining(c))
    return _re.sub(r"[^a-z0-9]+", "", ascii_only.lower())


# index nom replié -> clé canonique de COUNTRIES
_FOLDED_INDEX = {_fold(k): k for k in COUNTRIES}

# Alias explicites : noms usuels/officiels qui ne se replient PAS sur la clé
# canonique. Sans eux, `resolve_country` rejette des saisies légitimes.
# 'Royaume-Uni' est le cas signalé par Paul le 10/09 : il renvoyait EUR au lieu
# de GBP. 'Hong Kong' est l'orthographe correcte ; la clé Shopify porte la
# faute 'Honk Hong' et on ne la corrige pas côté code (le nom live fait loi).
# Les variantes purement accentuées ('Koweit', 'Bahrein') sont déjà couvertes
# par le repli et n'ont pas besoin d'alias.
_ALIASES = {
    "royaumeuni": "UK",
    "grandebretagne": "UK",
    "gb": "UK",
    "hongkong": "Honk Hong",
    "coreedusud": "Corée du Sud",
    "coree": "Corée du Sud",
    "singapour": "SINGAPOUR",
    "estonie": "ESTONIE",
    "etatsunis": "USA",
    "espagne": "Espagne",
    "emiratsarabesunis": "Émirats Arabes Unis",
    "republiquetcheque": "République tchèque",
    "tchequie": "République tchèque",
}
for _alias, _target in _ALIASES.items():
    assert _target in COUNTRIES, f"_ALIASES pointe sur un pays absent : {_target}"
    _FOLDED_INDEX.setdefault(_alias, _target)


def suggest_country_names(name: str, limit: int = 3) -> list:
    """
    Noms canoniques proches d'une saisie. Sert à transformer une erreur muette
    en message actionnable ('Royaume-Uni' -> 'UK').
    """
    import difflib

    folded = _fold(name)
    if not folded:
        return []
    # 1) sous-chaîne (attrape 'Nouvelle' -> 'Nouvelle Zélande')
    subs = [k for f, k in _FOLDED_INDEX.items() if folded in f or f in folded]
    # 2) proximité lexicale
    close = difflib.get_close_matches(folded, list(_FOLDED_INDEX.keys()), n=limit, cutoff=0.6)
    out = []
    for cand in subs + [_FOLDED_INDEX[c] for c in close]:
        if cand not in out:
            out.append(cand)
    return out[:limit]


def resolve_country(name: str) -> str:
    """
    Renvoie la clé canonique de COUNTRIES pour un nom saisi.
    Tolère casse, accents et ponctuation ; lève UnknownCountryError sinon.
    JAMAIS de fallback EUR/1.0 : un nom faux doit échouer, pas produire un prix.
    """
    if name in COUNTRIES:  # chemin rapide, cas nominal
        return name
    canonical = _FOLDED_INDEX.get(_fold(name))
    if canonical:
        return canonical
    raise UnknownCountryError(name, suggest_country_names(name))


def is_known_country(name: str) -> bool:
    """Variante non levante de resolve_country, pour filtrer une liste."""
    return name in COUNTRIES or _fold(name) in _FOLDED_INDEX


def _end_99(p: float) -> float:
    return float(_math.floor(p)) + 0.99


def _end_95(p: float) -> float:
    return float(_math.floor(p)) + 0.95


def _end_00(p: float) -> float:
    return float(round(p))


def _end_9_int(p: float) -> float:
    base = int(p)
    last = base % 10
    if last == 9:
        return float(base)
    if last < 9:
        return float(base - last + 9) if base >= 10 else 9.0
    return float(base - 1)


def _end_000(p: float) -> float:
    # max(...,1) : sans ce garde, un prix < 500 tombait à 0 (produit gratuit).
    return float(max(round(p / 1000), 1) * 1000)


def _end_990(p: float) -> float:
    base = int(p)
    if base >= 10000:
        return float((base // 1000) * 1000 + 990)
    if base >= 1000:
        return float((base // 100) * 100 + 90)
    # branche < 1000 : absente de la version countries.py d'origine, qui
    # renvoyait alors un négatif pour les petits montants.
    return float((base // 10) * 10 + 9)


def _end_kr(p: float) -> float:
    return float(round(p / 5) * 5)


ENDING_FUNCS = {
    "99": _end_99,
    "95": _end_95,
    "00": _end_00,
    "9_int": _end_9_int,
    "000": _end_000,
    "990": _end_990,
    "kr": _end_kr,
}


def apply_ending(price: float, country: str) -> float:
    """
    Applique la terminaison psychologique du pays. Chemin unique pour tous les
    routers. Lève sur pays inconnu (resolve_country) ou terminaison inconnue.
    """
    canonical = resolve_country(country)
    ending = COUNTRIES[canonical]["ending"]
    func = ENDING_FUNCS.get(ending)
    if func is None:
        raise ValueError(
            f"Terminaison '{ending}' inconnue pour '{canonical}'. "
            f"Valides : {sorted(ENDING_FUNCS)}"
        )
    return func(price)


def get_exchange_rate_strict(country: str) -> float:
    """Taux de change. Lève sur pays inconnu au lieu de renvoyer 1.0."""
    return COUNTRIES[resolve_country(country)]["exchange_rate"]


def get_currency_strict(country: str) -> str:
    """Devise déclarée. Lève sur pays inconnu au lieu de renvoyer 'EUR'."""
    return COUNTRIES[resolve_country(country)]["currency"]


# ─── AUTO-CONTRÔLES D'INTÉGRITÉ (au chargement du module) ──────────────────
# Un garde-fou doit pouvoir se déclencher : ceux-ci échouent au démarrage de
# l'app si la config devient incohérente, plutôt que de produire des prix faux
# en silence pendant des semaines.
_bad_endings = {k: v["ending"] for k, v in COUNTRIES.items() if v["ending"] not in ENDING_FUNCS}
assert not _bad_endings, f"countries.py : terminaison(s) inconnue(s) -> {_bad_endings}"

_bad_folds = [k for k in COUNTRIES if _FOLDED_INDEX.get(_fold(k)) != k]
assert not _bad_folds, f"countries.py : noms qui collisionnent après normalisation -> {_bad_folds}"

for _k, _v in COUNTRIES.items():
    assert _v.get("currency"), f"countries.py : devise manquante pour '{_k}'"
    assert isinstance(_v.get("exchange_rate"), (int, float)), \
        f"countries.py : exchange_rate non numérique pour '{_k}'"
