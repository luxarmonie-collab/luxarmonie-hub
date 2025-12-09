"""
Configuration des pays et marchés
Contient tous les 57 marchés Luxarmonie
"""

COUNTRIES = {
    # Europe - EUR
    "France": {"currency": "EUR", "ending": 0.99, "vat": 0.20, "exchange_rate": 1, "adjustment": "none"},
    "Allemagne": {"currency": "EUR", "ending": 0.95, "vat": 0.19, "exchange_rate": 1, "adjustment": "none"},
    "Italie": {"currency": "EUR", "ending": 0.00, "vat": 0.22, "exchange_rate": 1, "adjustment": "none"},
    "Espagne": {"currency": "EUR", "ending": 0.99, "vat": 0.21, "exchange_rate": 1, "adjustment": "none"},
    "Belgique": {"currency": "EUR", "ending": 0.99, "vat": 0.21, "exchange_rate": 1, "adjustment": "none"},
    "Pays-Bas": {"currency": "EUR", "ending": 0.99, "vat": 0.21, "exchange_rate": 1, "adjustment": "none"},
    "Luxembourg": {"currency": "EUR", "ending": 0.99, "vat": 0.17, "exchange_rate": 1, "adjustment": "none"},
    "Autriche": {"currency": "EUR", "ending": 0.95, "vat": 0.20, "exchange_rate": 1, "adjustment": "none"},
    "Portugal": {"currency": "EUR", "ending": 0.99, "vat": 0.23, "exchange_rate": 1, "adjustment": "none"},
    "Irlande": {"currency": "EUR", "ending": 0.99, "vat": 0.23, "exchange_rate": 1, "adjustment": "none"},
    "Grèce": {"currency": "EUR", "ending": 0.99, "vat": 0.24, "exchange_rate": 1, "adjustment": "none"},
    "Finlande": {"currency": "EUR", "ending": 0.99, "vat": 0.24, "exchange_rate": 1, "adjustment": "none"},
    "Estonie": {"currency": "EUR", "ending": 0.99, "vat": 0.20, "exchange_rate": 1, "adjustment": "none"},
    "Croatie": {"currency": "EUR", "ending": 0.99, "vat": 0.25, "exchange_rate": 1, "adjustment": "none"},
    
    # Europe - Autres devises
    "UK": {"currency": "GBP", "ending": 0.99, "vat": 0.20, "exchange_rate": 0.86, "adjustment": "none"},
    "Suisse": {"currency": "CHF", "ending": 0.95, "vat": 0.077, "exchange_rate": 0.97, "adjustment": "none"},
    "Pologne": {"currency": "PLN", "ending": 0.99, "vat": 0.23, "exchange_rate": 4.32, "adjustment": "none"},
    "Danemark": {"currency": "DKK", "ending": 5, "vat": 0.25, "exchange_rate": 7.46, "adjustment": "none"},
    "Suède": {"currency": "SEK", "ending": 5, "vat": 0.25, "exchange_rate": 11.5, "adjustment": "none"},
    "Norvège": {"currency": "NOK", "ending": 0.00, "vat": 0.25, "exchange_rate": 11.8, "adjustment": "none"},
    "Hongrie": {"currency": "HUF", "ending": 990, "vat": 0.27, "exchange_rate": 395, "adjustment": "none"},
    "République Tchèque": {"currency": "CZK", "ending": 990, "vat": 0.21, "exchange_rate": 25.3, "adjustment": "none"},
    "Turquie": {"currency": "TRY", "ending": 0.99, "vat": 0.20, "exchange_rate": 34.5, "adjustment": "none"},
    "Serbie": {"currency": "RSD", "ending": 990, "vat": 0.20, "exchange_rate": 117, "adjustment": "none"},
    
    # Amérique du Nord
    "USA": {"currency": "USD", "ending": 0.99, "vat": 0, "exchange_rate": 1.09, "adjustment": "none"},
    "Canada": {"currency": "CAD", "ending": 0.99, "vat": 0.05, "exchange_rate": 1.48, "adjustment": "none"},
    "Mexique": {"currency": "MXN", "ending": 0.99, "vat": 0.16, "exchange_rate": 18.7, "adjustment": "none"},
    
    # Amérique du Sud
    "Brésil": {"currency": "BRL", "ending": 0.00, "vat": 0, "exchange_rate": 5.3, "adjustment": "none"},
    "Argentine": {"currency": "ARS", "ending": 0.00, "vat": 0.21, "exchange_rate": 980, "adjustment": "none"},
    "Chili": {"currency": "CLP", "ending": 1000, "vat": 0.19, "exchange_rate": 980, "adjustment": "none"},
    "Colombie": {"currency": "COP", "ending": 1000, "vat": 0.19, "exchange_rate": 4300, "adjustment": "none"},
    "Pérou": {"currency": "PEN", "ending": 0.99, "vat": 0.18, "exchange_rate": 4.05, "adjustment": "none"},
    "Uruguay": {"currency": "UYU", "ending": 0.00, "vat": 0.22, "exchange_rate": 42, "adjustment": "none"},
    "Paraguay": {"currency": "PYG", "ending": 1000, "vat": 0.10, "exchange_rate": 7800, "adjustment": "none"},
    "Bolivie": {"currency": "BOB", "ending": 0.99, "vat": 0.13, "exchange_rate": 6.9, "adjustment": "none"},
    "Équateur": {"currency": "USD", "ending": 0.00, "vat": 0.12, "exchange_rate": 1.09, "adjustment": "none"},
    "Costa Rica": {"currency": "CRC", "ending": 0.00, "vat": 0.13, "exchange_rate": 530, "adjustment": "none"},
    "Guatemala": {"currency": "GTQ", "ending": 0.99, "vat": 0.12, "exchange_rate": 7.8, "adjustment": "none"},
    "Honduras": {"currency": "HNL", "ending": 0.99, "vat": 0.15, "exchange_rate": 25, "adjustment": "none"},
    "Panama": {"currency": "USD", "ending": 0.00, "vat": 0.07, "exchange_rate": 1.09, "adjustment": "none"},
    "Salvador": {"currency": "USD", "ending": 0.00, "vat": 0.13, "exchange_rate": 1.09, "adjustment": "none"},
    "République Dominicaine": {"currency": "DOP", "ending": 0.00, "vat": 0.18, "exchange_rate": 60, "adjustment": "none"},
    
    # Asie-Pacifique
    "Australie": {"currency": "AUD", "ending": 0.99, "vat": 0.10, "exchange_rate": 1.65, "adjustment": "none"},
    "Nouvelle-Zélande": {"currency": "NZD", "ending": 0.99, "vat": 0.15, "exchange_rate": 1.78, "adjustment": "none"},
    "Hong Kong": {"currency": "HKD", "ending": 0.00, "vat": 0, "exchange_rate": 8.5, "adjustment": "none"},
    "Singapour": {"currency": "SGD", "ending": 0.00, "vat": 0.09, "exchange_rate": 1.46, "adjustment": "none"},
    "Malaisie": {"currency": "MYR", "ending": 0.00, "vat": 0.10, "exchange_rate": 4.8, "adjustment": "none"},
    
    # Moyen-Orient
    "Arabie Saoudite": {"currency": "SAR", "ending": 9, "vat": 0.15, "exchange_rate": 4.1, "adjustment": "none"},
    "UAE": {"currency": "AED", "ending": 9, "vat": 0.05, "exchange_rate": 4.0, "adjustment": "none"},
    "Qatar": {"currency": "QAR", "ending": 9, "vat": 0, "exchange_rate": 3.97, "adjustment": "none"},
    "Koweït": {"currency": "KWD", "ending": 0.00, "vat": 0, "exchange_rate": 0.335, "adjustment": "none"},
    "Bahreïn": {"currency": "BHD", "ending": 0.00, "vat": 0.10, "exchange_rate": 0.41, "adjustment": "none"},
    "Oman": {"currency": "OMR", "ending": 0.00, "vat": 0.05, "exchange_rate": 0.42, "adjustment": "none"},
    "Jordanie": {"currency": "JOD", "ending": 0.00, "vat": 0.16, "exchange_rate": 0.77, "adjustment": "none"},
    "Liban": {"currency": "USD", "ending": 0.00, "vat": 0.11, "exchange_rate": 1.09, "adjustment": "none"},
    "Israël": {"currency": "ILS", "ending": 0.99, "vat": 0.17, "exchange_rate": 3.9, "adjustment": "none"},
    
    # Afrique
    "Afrique du Sud": {"currency": "ZAR", "ending": 0.00, "vat": 0.15, "exchange_rate": 19.5, "adjustment": "none"},
}


def get_all_countries():
    """Retourne la liste de tous les noms de pays"""
    return list(COUNTRIES.keys())


def get_country_config(country_name: str):
    """Retourne la configuration d'un pays"""
    return COUNTRIES.get(country_name, None)
