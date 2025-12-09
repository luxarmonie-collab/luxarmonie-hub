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
        "exchange_rate": 7.46,
        "culture": "low-context"
    },
    "Suède": {
        "currency": "SEK",
        "ending": "kr",
        "vat": 0.25,
        "adjustment": "vat",
        "exchange_rate": 11.20,
        "culture": "low-context"
    },
    "Norvège": {
        "currency": "NOK",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 11.80,
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
        "exchange_rate": 4.28,
        "culture": "low-context"
    },
    "République tchèque": {
        "currency": "CZK",
        "ending": "990",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 25.10,
        "culture": "low-context"
    },
    "Serbie": {
        "currency": "RSD",
        "ending": "990",
        "vat": 0.21,
        "adjustment": "vat",
        "exchange_rate": 117,
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
        "exchange_rate": 1.16,
        "culture": "low-context"
    },
    "Canada": {
        "currency": "CAD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.63,
        "culture": "low-context"
    },
    "Mexique": {
        "currency": "MXN",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 23.00,
        "culture": "low-context"
    },
    
    # === AMÉRIQUE DU SUD ===
    "Brésil": {
        "currency": "BRL",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 5.80,
        "culture": "high-context"
    },
    "Argentine": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
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
        "exchange_rate": 4900,
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
        "exchange_rate": 50.00,
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
        "exchange_rate": 4.35,
        "culture": "high-context"
    },
    "Émirats Arabes Unis": {
        "currency": "AED",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.26,
        "culture": "high-context"
    },
    "Qatar": {
        "currency": "QAR",
        "ending": "9_int",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 4.22,
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
    "Australie": {
        "currency": "AUD",
        "ending": "99",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1.76,
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
        "exchange_rate": 40.00,
        "culture": "low-context"
    },
    
    # === AFRIQUE ===
    "Afrique du Sud": {
        "currency": "EUR",
        "ending": "00",
        "vat": 0,
        "adjustment": "minus_10",
        "exchange_rate": 1,
        "culture": "high-context"
    },
}

# Devises qui n'ont pas de décimales
NO_DECIMAL_CURRENCIES = [
    "HUF", "CZK", "RSD", "CLP", "COP", "PYG", 
    "SAR", "QAR", "AED", "DKK", "SEK", "NOK", 
    "HKD", "CRC", "UYU", "DOP"
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
