"""
Router pour les opérations de pricing
V3 - Calcul basé sur prix ACTUEL du marché + tous les produits
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.services.pricing_engine import pricing_engine, PricingOperation
from app.services.price_cache import price_cache
from app.config.countries import COUNTRIES, get_all_countries
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import math

router = APIRouter(tags=["pricing"])

# Variable globale pour suivre la progression de l'apply
apply_progress = {
    "active": False,
    "current_market": "",
    "markets_done": 0,
    "total_markets": 0,
    "variants_updated": 0,
    "errors": []
}


# ========================================
# MODELS
# ========================================

class PricingPreviewRequest(BaseModel):
    countries: List[str]
    product_ids: Optional[List[str]] = None
    variant_ids: Optional[List[str]] = None
    all_products: bool = False  # NEW: récupérer tous les produits
    base_adjustment: float = 0.10  # +10% par défaut
    apply_vat: bool = False
    discount: float = 0.40  # Pour le compare_at
    use_market_price: bool = True  # NEW: utiliser le prix actuel du marché


class PricingApplyRequest(BaseModel):
    countries: List[str]
    product_ids: Optional[List[str]] = None
    variant_ids: Optional[List[str]] = None
    all_products: bool = False
    base_adjustment: float = 0.10
    apply_vat: bool = False
    discount: float = 0.40
    use_market_price: bool = True
    dry_run: bool = False


class SingleProductPricingRequest(BaseModel):
    sku: str
    base_price_eur: float
    countries: List[str]
    discount: float = 0.40


class ExchangeRatesUpdate(BaseModel):
    rates: dict


# ========================================
# HELPERS
# ========================================

# ========================================
# FONCTIONS DE TERMINAISON PAR CULTURE
# ========================================

def round_99(price: float) -> float:
    """Low-context: .99 (USA, UK, France, Canada, Australie...)"""
    return float(math.floor(price)) + 0.99

def round_95(price: float) -> float:
    """Allemagne, Autriche, Suisse: .95"""
    return float(math.floor(price)) + 0.95

def round_00(price: float) -> float:
    """High-context: .00 (Brésil, Argentine, Italie, Hong Kong, Singapour...)"""
    return float(round(price))

def round_9_int(price: float) -> float:
    """Moyen-Orient: entier finissant en 9"""
    base = int(price)
    last = base % 10
    if last == 9:
        return float(base)
    elif last < 9:
        return float(base - last + 9) if base >= 10 else float(9)
    return float(base - 1)

def round_000(price: float) -> float:
    """Grandes devises: milliers (Chili, Colombie, Paraguay)"""
    thousands = round(price / 1000)
    return float(max(thousands, 1) * 1000)

def round_990(price: float) -> float:
    """HUF, CZK, RSD: en 990/90/9"""
    base = int(price)
    if base >= 10000:
        return float((base // 1000) * 1000 + 990)
    elif base >= 1000:
        return float((base // 100) * 100 + 90)
    else:
        return float((base // 10) * 10 + 9)

def round_kr(price: float) -> float:
    """Scandinave DKK/SEK: multiples de 5"""
    return float(round(price / 5) * 5)


def format_price_for_country(price: float, country: str) -> str:
    """
    Formate un prix selon les conventions du pays.
    Retourne une string avec le bon nombre de décimales.
    """
    config = COUNTRIES.get(country, {})
    currency = config.get("currency", "EUR")

    # Devises sans centimes
    no_decimal_currencies = ["HUF", "CLP", "COP", "PYG", "KRW", "JPY", "VND"]

    if currency in no_decimal_currencies:
        return f"{int(round(price))}"
    else:
        return f"{price:.2f}"


# Mapping des pays vers leur fonction de terminaison
COUNTRY_ROUNDING = {
    # .99
    'France': round_99,
    'USA': round_99,
    'UK': round_99,
    'Canada': round_99,
    'Australie': round_99,
    'Nouvelle Zelande': round_99,
    'Nouvelle-Zélande': round_99,
    'Belgique': round_99,
    'Espagne': round_99,
    'Pays-Bas': round_99,
    'Luxembourg': round_99,
    'Estonie': round_99,
    'Grece': round_99,
    'Grèce': round_99,
    'Irlande': round_99,
    'Portugal': round_99,
    'Croatie': round_99,
    'Finlande': round_99,
    'Pologne': round_99,
    'Mexique': round_99,
    'Israel': round_99,
    'Israël': round_99,
    'Perou': round_99,
    'Pérou': round_99,
    'Bolivie': round_99,
    'Guatemala': round_99,
    'Honduras': round_99,
    'Turquie': round_99,
    
    # .95
    'Allemagne': round_95,
    'Germany': round_95,
    'Autriche': round_95,
    'Suisse': round_95,
    
    # .00 (high-context / entier)
    'Italie': round_00,
    'Bresil': round_00,
    'Brésil': round_00,
    'Hong Kong': round_00,
    'Singapour': round_00,
    'Argentine': round_00,
    'Norvege': round_00,
    'Norvège': round_00,
    'Uruguay': round_00,
    'Costa Rica': round_00,
    'Afrique du Sud': round_00,
    'Oman': round_00,
    'Panama': round_00,
    'Salvador': round_00,
    'Malaisie': round_00,
    'Jordanie': round_00,
    'Koweit': round_00,
    'Koweït': round_00,
    'Liban': round_00,
    'Bahrein': round_00,
    'Bahreïn': round_00,
    'Equateur': round_00,
    'Équateur': round_00,
    'Republique Dominicaine': round_00,
    'République Dominicaine': round_00,
    
    # Scandinave (multiples de 5)
    'Danemark': round_kr,
    'Suede': round_kr,
    'Suède': round_kr,
    
    # 990
    'Hongrie': round_990,
    'Republique Tcheque': round_990,
    'République Tchèque': round_990,
    'Tchéquie': round_990,
    'Serbie': round_990,
    
    # Entier en 9 (Moyen-Orient)
    'Arabie Saoudite': round_9_int,
    'UAE': round_9_int,
    'Émirats arabes unis': round_9_int,
    'Qatar': round_9_int,
    
    # Milliers
    'Chili': round_000,
    'Colombie': round_000,
    'Paraguay': round_000,
}


def apply_psychological_ending(price: float, country: str) -> float:
    """Applique la terminaison psychologique selon le pays"""
    # Utiliser la fonction de terminaison appropriée
    round_func = COUNTRY_ROUNDING.get(country)
    
    if round_func:
        return round_func(price)
    
    # Fallback: utiliser la config COUNTRIES si disponible
    config = COUNTRIES.get(country, {})
    ending = config.get("ending", 0.99)
    
    try:
        ending = float(ending)
    except (ValueError, TypeError):
        ending = 0.99
    
    # Si ending > 1, c'est en centimes (ex: 99), convertir en décimal (0.99)
    if ending >= 1:
        ending = ending / 100
    
    base = math.floor(price)
    return round(base + ending, 2)


def calculate_compare_at(price: float, discount_percent: float) -> float:
    """
    Calcule le compare_at pour afficher une réduction
    Si price = 89.99 et discount = 0.40, alors compare_at = 89.99 / 0.60 = 149.98
    """
    if discount_percent <= 0 or discount_percent >= 1:
        return price
    
    return price / (1 - discount_percent)


# ========================================
# HISTORIQUE
# ========================================

pricing_history = []


def log_operation(operation_type: str, details: dict):
    pricing_history.append({
        "id": len(pricing_history) + 1,
        "timestamp": datetime.now().isoformat(),
        "type": operation_type,
        "details": details
    })
    if len(pricing_history) > 100:
        pricing_history.pop(0)


# ========================================
# ENDPOINTS
# ========================================

@router.get("/config")
async def get_pricing_config():
    """
    Configuration des marchés disponibles
    Utilise le cache si chargé, sinon Shopify, sinon config statique.

    IMPORTANT: Retourne TOUS les marchés, y compris ceux sans PriceList.
    """
    from app.services.price_cache import price_cache
    import logging
    logger = logging.getLogger(__name__)

    # 1. Si le cache est chargé ET contient des données, utiliser les marchés du cache
    if price_cache.is_loaded and len(price_cache._cache) > 0:
        logger.info(f"CONFIG: Using cache ({len(price_cache._cache)} markets)")
        countries = []
        for market_name, market_data in price_cache._cache.items():
            currency = market_data.get("currency", "EUR")
            config = COUNTRIES.get(market_name, {})
            has_pricelist = market_data.get("hasPriceList", False)
            prices_count = len(market_data.get("prices", {}))

            countries.append({
                "name": market_name,
                "currency": currency,
                "ending": config.get("ending", 0.99),
                "vat": config.get("vat", 0),
                "exchange_rate": config.get("exchange_rate", 1),
                "adjustment": config.get("adjustment", "none"),
                "prices_count": prices_count,
                "hasPriceList": has_pricelist,
                "usesBasePrices": market_data.get("usesBasePrices", False)
            })
        countries.sort(key=lambda x: x["name"])
        return {"countries": countries, "source": "cache"}

    # 2. Toujours essayer Shopify (même pendant le chargement du cache)
    logger.info("CONFIG: Cache not ready, fetching from Shopify...")
    shopify_error = None
    try:
        markets = await shopify_service.get_all_markets()

        if markets and len(markets) > 0:
            logger.info(f"CONFIG: Got {len(markets)} markets from Shopify")

            countries = []
            for market in markets:
                market_name = market["name"]
                price_list = market.get("priceList")

                # Récupérer la devise depuis PriceList ou currencySettings
                if price_list:
                    currency = price_list.get("currency", "EUR")
                else:
                    currency_settings = market.get("currencySettings", {})
                    base_currency = currency_settings.get("baseCurrency", {})
                    currency = base_currency.get("currencyCode", "EUR")

                config = COUNTRIES.get(market_name, {})
                countries.append({
                    "name": market_name,
                    "currency": currency,
                    "ending": config.get("ending", 0.99),
                    "vat": config.get("vat", 0),
                    "exchange_rate": config.get("exchange_rate", 1),
                    "adjustment": config.get("adjustment", "none"),
                    "hasPriceList": price_list is not None,
                    "usesBasePrices": price_list is None
                })
            countries.sort(key=lambda x: x["name"])
            return {"countries": countries, "source": "shopify"}
        else:
            shopify_error = "Shopify returned 0 markets"
            logger.warning(f"CONFIG: {shopify_error}")
    except Exception as e:
        shopify_error = str(e)
        logger.error(f"CONFIG ERROR: Failed to load from Shopify: {e}")
        import traceback
        traceback.print_exc()

    # 3. Fallback sur config statique
    logger.warning(f"CONFIG: Using static fallback ({len(COUNTRIES)} countries)")
    static_countries = [
        {
            "name": name,
            "currency": config["currency"],
            "ending": config["ending"],
            "vat": config["vat"],
            "exchange_rate": config["exchange_rate"],
            "adjustment": config["adjustment"],
            "hasPriceList": True,  # On assume que la config statique a des prix
            "usesBasePrices": False
        }
        for name, config in COUNTRIES.items()
    ]
    static_countries.sort(key=lambda x: x["name"])

    return {
        "countries": static_countries,
        "source": "static",
        "warning": f"Données Shopify non disponibles ({shopify_error}). Utilisation de la config statique."
    }


@router.put("/exchange-rates")
async def update_exchange_rates(update: ExchangeRatesUpdate):
    """Met à jour les taux de change"""
    updated = []
    errors = []
    
    for country, rate in update.rates.items():
        if country in COUNTRIES:
            old_rate = COUNTRIES[country]["exchange_rate"]
            COUNTRIES[country]["exchange_rate"] = rate
            updated.append({"country": country, "old": old_rate, "new": rate})
        else:
            errors.append(f"Country '{country}' not found")
    
    log_operation("exchange_rates_update", {"updated": updated})
    
    return {"success": len(errors) == 0, "updated": updated, "errors": errors}


@router.post("/calculate")
async def calculate_price(request: SingleProductPricingRequest):
    """Calcule le prix pour un produit sur plusieurs pays"""
    countries = get_all_countries() if "all" in request.countries else request.countries
    
    operation = PricingOperation(
        base_adjustment=-0.12,
        apply_vat=True,
        compare_at_markup=request.discount
    )
    
    results = []
    for country in countries:
        calc = pricing_engine.calculate_price(request.base_price_eur, country, operation)
        if calc:
            results.append({
                "country": country,
                "currency": calc.currency,
                "price": calc.final_price,
                "compareAt": calc.compare_at_price,
                "discount": f"{calc.discount_percentage}%"
            })
    
    return {
        "sku": request.sku,
        "base_price_eur": request.base_price_eur,
        "results": results
    }


@router.post("/preview")
async def preview_pricing(request: PricingPreviewRequest):
    """
    Prévisualise les changements de prix
    V3: Calcul basé sur prix ACTUEL du marché
    """
    try:
        countries = get_all_countries() if "all" in request.countries else request.countries
        
        # ========================================
        # 1. RÉCUPÉRER LES PRODUITS
        # ========================================
        variants_data = []
        
        if request.all_products:
            # Récupérer TOUS les produits
            products = await shopify_service.get_all_products(max_products=2000)
            
            for product in products:
                for variant in product["variants"]:
                    variant_id = variant.get("id")
                    
                    if request.variant_ids and variant_id not in request.variant_ids:
                        continue
                    
                    variants_data.append({
                        "variant_id": variant_id,
                        "sku": variant.get("sku", ""),
                        "title": f"{product['title']} - {variant['title']}",
                        "product_title": product['title'],
                        "variant_title": variant['title'],
                        "base_price": float(variant["price"]) if variant.get("price") else 0
                    })
                    
        elif request.product_ids:
            # Produits spécifiques
            for pid in request.product_ids:
                product = await shopify_service.get_product_by_id(pid)
                if product:
                    for variant in product["variants"]:
                        variant_id = variant.get("id")
                        
                        if request.variant_ids and variant_id not in request.variant_ids:
                            continue
                        
                        variants_data.append({
                            "variant_id": variant_id,
                            "sku": variant.get("sku", ""),
                            "title": f"{product['title']} - {variant['title']}",
                            "product_title": product['title'],
                            "variant_title": variant['title'],
                            "base_price": float(variant["price"]) if variant.get("price") else 0
                        })
        else:
            # Recherche (limité à 250)
            raw_products = await shopify_service.search_products("", 250)
            for product in raw_products:
                for variant in product["variants"]:
                    variant_id = variant.get("id")
                    
                    if request.variant_ids and variant_id not in request.variant_ids:
                        continue
                    
                    variants_data.append({
                        "variant_id": variant_id,
                        "sku": variant.get("sku", ""),
                        "title": f"{product['title']} - {variant['title']}",
                        "product_title": product['title'],
                        "variant_title": variant['title'],
                        "base_price": float(variant["price"]) if variant.get("price") else 0
                    })
        
        if not variants_data:
            return {
                "summary": {"total_products": 0, "total_countries": 0, "total_updates": 0},
                "preview": []
            }
        
        # ========================================
        # 2. RÉCUPÉRER LES PRIX ACTUELS PAR MARCHÉ
        # ========================================
        all_variant_ids = [v["variant_id"] for v in variants_data if v["variant_id"]]
        
        market_prices = {}
        cache_used = False
        
        if request.use_market_price:
            # Essayer d'abord le cache
            from app.services.price_cache import price_cache
            
            if price_cache.is_loaded:
                # Utiliser le cache (instantané!)
                market_prices = price_cache.get_prices_for_variants(
                    variant_ids=all_variant_ids,
                    market_names=countries
                )
                cache_used = True
                print(f"Using cache: found prices for {len(market_prices)} markets")
            else:
                # Fallback: requêtes API (lent)
                print("Cache not loaded, fetching from API...")
                try:
                    market_prices = await shopify_service.get_variant_prices_by_market(
                        variant_ids=all_variant_ids,
                        market_names=countries
                    )
                except Exception as e:
                    print(f"Warning: Could not fetch market prices: {e}")
        
        # ========================================
        # 3. CALCULER LES NOUVEAUX PRIX
        # ========================================
        preview = []
        
        for variant in variants_data:
            variant_id = variant["variant_id"]
            
            for country in countries:
                config = COUNTRIES.get(country, {})
                currency = config.get("currency", "EUR")
                
                # Récupérer le prix actuel du marché
                current_price = None
                current_compare_at = None
                current_currency = currency
                
                if country in market_prices:
                    market_data = market_prices[country]
                    current_currency = market_data.get("currency", currency)
                    
                    prices = market_data.get("prices", {})
                    if variant_id in prices:
                        price_info = prices[variant_id]
                        current_price = float(price_info.get("price", 0)) if price_info.get("price") else None
                        current_compare_at = float(price_info.get("compareAtPrice", 0)) if price_info.get("compareAtPrice") else None
                
                # ========================================
                # CALCUL DU NOUVEAU PRIX
                # ========================================
                if request.use_market_price and current_price is not None:
                    # *** MODE PRIX MARCHÉ: Appliquer % sur prix actuel ***
                    raw_price = current_price * (1 + request.base_adjustment)
                    new_price = apply_psychological_ending(raw_price, country)
                    
                    # Compare At basé sur nouveau prix + discount
                    if request.discount > 0:
                        raw_compare_at = calculate_compare_at(new_price, request.discount)
                        compare_at_price = apply_psychological_ending(raw_compare_at, country)
                    else:
                        compare_at_price = new_price
                    
                    # Calculer le vrai % de réduction
                    if compare_at_price > new_price:
                        discount_percentage = round((1 - new_price / compare_at_price) * 100)
                    else:
                        discount_percentage = 0
                        
                else:
                    # *** MODE FALLBACK: Utiliser pricing_engine (conversion EUR) ***
                    operation = PricingOperation(
                        base_adjustment=request.base_adjustment,
                        apply_vat=request.apply_vat,
                        compare_at_markup=request.discount
                    )
                    
                    calc = pricing_engine.calculate_price(variant["base_price"], country, operation)
                    
                    if calc:
                        new_price = calc.final_price
                        compare_at_price = calc.compare_at_price
                        discount_percentage = calc.discount_percentage
                        current_currency = calc.currency
                    else:
                        continue
                
                preview.append({
                    "sku": variant["sku"],
                    "title": variant["title"],
                    "product_title": variant["product_title"],
                    "variant_title": variant["variant_title"],
                    "variant_id": variant_id,
                    "country": country,
                    "currency": current_currency,
                    # Prix actuels
                    "current_price": current_price,
                    "current_compare_at": current_compare_at,
                    # Nouveaux prix
                    "new_price": new_price,
                    "compare_at_price": compare_at_price,
                    "discount_percentage": discount_percentage,
                    # Référence
                    "base_price_eur": variant["base_price"]
                })
        
        return {
            "summary": {
                "total_products": len(variants_data),
                "total_countries": len(countries),
                "total_updates": len(preview),
                "markets_with_prices": len(market_prices),
                "cache_used": cache_used
            },
            "preview": preview[:1000]  # Limite à 1000 pour l'affichage
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_pricing(request: PricingApplyRequest):
    """
    Applique les changements de prix sur Shopify
    V3: Support tous produits + calcul sur prix marché + mise à jour cache
    """
    global apply_progress
    
    try:
        # Initialiser la progression
        apply_progress = {
            "active": True,
            "current_market": "Préparation...",
            "markets_done": 0,
            "total_markets": len(request.countries),
            "variants_updated": 0,
            "errors": []
        }
        
        # Générer la preview pour avoir les prix calculés
        preview_request = PricingPreviewRequest(
            countries=request.countries,
            product_ids=request.product_ids,
            variant_ids=request.variant_ids,
            all_products=request.all_products,
            base_adjustment=request.base_adjustment,
            apply_vat=request.apply_vat,
            discount=request.discount,
            use_market_price=request.use_market_price
        )
        
        preview_result = await preview_pricing(preview_request)
        preview_data = preview_result["preview"]
        
        if request.dry_run:
            apply_progress["active"] = False
            return {
                "applied": False,
                "dry_run": True,
                "would_update": len(preview_data),
                "preview": preview_data[:50]
            }
        
        # Grouper les mises à jour par pays/marché
        updates_by_country = {}
        for item in preview_data:
            country = item["country"]
            if country not in updates_by_country:
                updates_by_country[country] = []
            updates_by_country[country].append({
                "variant_id": item["variant_id"],
                "price": item["new_price"],
                "compare_at_price": item["compare_at_price"]
            })
        
        apply_progress["total_markets"] = len(updates_by_country)
        
        results = {"success": [], "errors": [], "updated_count": 0}
        cache_updates = []  # Pour mettre à jour le cache
        
        for idx, (country, updates) in enumerate(updates_by_country.items()):
            # Mettre à jour la progression
            apply_progress["current_market"] = country
            apply_progress["markets_done"] = idx
            
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    updated_count = update_result.get("updated", len(updates))
                    results["success"].append({
                        "country": country,
                        "updated": updated_count
                    })
                    results["updated_count"] += updated_count
                    apply_progress["variants_updated"] += updated_count
                    
                    # Préparer les mises à jour du cache
                    for update in updates:
                        cache_updates.append({
                            "market": country,
                            "variant_id": update["variant_id"],
                            "price": update["price"],
                            "compare_at_price": update["compare_at_price"]
                        })
                else:
                    error_msg = f"{country}: {update_result.get('error')}"
                    results["errors"].append(error_msg)
                    apply_progress["errors"].append(error_msg)
                    if update_result.get("errors"):
                        for err in update_result["errors"]:
                            results["errors"].append(f"{country}: {err}")
                            apply_progress["errors"].append(f"{country}: {err}")
                            
            except Exception as e:
                error_msg = f"{country}: {str(e)}"
                results["errors"].append(error_msg)
                apply_progress["errors"].append(error_msg)
        
        # Mettre à jour le cache avec les nouveaux prix
        if cache_updates:
            cache_updated = price_cache.update_prices(cache_updates, save=True)
            results["cache_updated"] = cache_updated
        
        # Finaliser la progression
        apply_progress["current_market"] = "Terminé"
        apply_progress["markets_done"] = len(updates_by_country)
        apply_progress["active"] = False
        
        log_operation("pricing_apply", {
            "countries": list(updates_by_country.keys()),
            "total_updates": results["updated_count"],
            "cache_updates": len(cache_updates),
            "errors_count": len(results["errors"])
        })
        
        return {
            "applied": True,
            "results": results
        }
    
    except Exception as e:
        apply_progress["active"] = False
        apply_progress["errors"].append(str(e))
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/apply-progress")
async def get_apply_progress():
    """Retourne la progression de l'apply en cours"""
    return apply_progress


@router.get("/history")
async def get_history():
    """Récupère l'historique des opérations"""
    return {
        "total": len(pricing_history),
        "operations": pricing_history[-20:]
    }


# ========================================
# PROMOS ALÉATOIRES
# ========================================

import random

class RandomPromoRequest(BaseModel):
    """Paramètres pour les promos aléatoires"""
    countries: List[str]                    # Marchés cibles
    catalog_percentage: float = 50.0        # % du catalogue à mettre en promo (0-100)
    min_discount: float = 10.0              # Réduction minimum (%)
    max_discount: float = 40.0              # Réduction maximum (%)
    seed: Optional[int] = None              # Seed pour reproductibilité (optionnel)


class RandomPromoApplyRequest(RandomPromoRequest):
    """Paramètres pour appliquer les promos"""
    dry_run: bool = False


@router.post("/random-promo/preview")
async def preview_random_promo(request: RandomPromoRequest):
    """
    Génère une preview des promos aléatoires.
    - Sélectionne X% des PRODUITS (pas variantes) aléatoirement
    - Attribue une réduction aléatoire entre min et max à chaque produit
    - Toutes les variantes d'un produit ont la même réduction
    """
    try:
        # Initialiser le générateur aléatoire
        if request.seed is not None:
            random.seed(request.seed)
        else:
            random.seed()
        
        # Récupérer tous les produits avec leurs variantes
        all_products = await shopify_service.get_all_products_with_variants()
        
        if not all_products:
            raise HTTPException(status_code=404, detail="Aucun produit trouvé")
        
        total_products = len(all_products)
        
        # Calculer combien de produits mettre en promo
        promo_count = int(total_products * (request.catalog_percentage / 100))
        promo_count = max(1, min(promo_count, total_products))  # Au moins 1, max tous
        
        # Sélectionner aléatoirement les produits
        selected_products = random.sample(all_products, promo_count)
        
        # Attribuer une réduction aléatoire à chaque produit
        product_discounts = {}
        for product in selected_products:
            discount = random.uniform(request.min_discount, request.max_discount)
            discount = round(discount, 0)  # Arrondir au %
            product_discounts[product["id"]] = discount
        
        # Déterminer les marchés
        if 'all' in request.countries:
            countries = price_cache.get_all_markets()
        else:
            countries = request.countries
        
        # Générer la preview
        preview_items = []
        
        for product in selected_products:
            product_id = product["id"]
            discount_pct = product_discounts[product_id]
            
            for variant in product.get("variants", []):
                variant_id = variant["id"]
                
                for country in countries:
                    # Récupérer le prix actuel du cache
                    cached = price_cache.get_price(country, variant_id)
                    
                    if cached:
                        current_price = float(cached.get("price", 0))
                        currency = cached.get("currency", "EUR")
                    else:
                        continue  # Pas de prix pour ce marché
                    
                    if current_price <= 0:
                        continue
                    
                    # Calculer le nouveau prix (prix actuel = nouveau compare_at, prix réduit = nouveau prix)
                    compare_at_price = current_price  # L'ancien prix devient le compare_at
                    reduction_factor = 1 - (discount_pct / 100)
                    new_price_raw = current_price * reduction_factor
                    
                    # Appliquer la terminaison psychologique
                    new_price = apply_psychological_ending(new_price_raw, country)
                    
                    # Formater
                    new_price_str = format_price_for_country(new_price, country)
                    compare_at_str = format_price_for_country(compare_at_price, country)
                    
                    preview_items.append({
                        "product_id": product_id,
                        "product_title": product.get("title", ""),
                        "variant_id": variant_id,
                        "variant_title": variant.get("title", ""),
                        "sku": variant.get("sku", ""),
                        "country": country,
                        "currency": currency,
                        "current_price": f"{current_price:.2f}",
                        "new_price": new_price_str,
                        "compare_at_price": compare_at_str,
                        "discount_percentage": discount_pct
                    })
        
        # Résumé par produit
        products_summary = []
        for product in selected_products:
            products_summary.append({
                "id": product["id"],
                "title": product.get("title", ""),
                "variants_count": len(product.get("variants", [])),
                "discount": product_discounts[product["id"]]
            })
        
        return {
            "summary": {
                "total_products_in_catalog": total_products,
                "products_selected": promo_count,
                "catalog_percentage": request.catalog_percentage,
                "min_discount": request.min_discount,
                "max_discount": request.max_discount,
                "total_markets": len(countries),
                "total_price_changes": len(preview_items)
            },
            "products": products_summary[:100],  # Limiter pour l'affichage
            "preview": preview_items[:500]  # Limiter pour l'affichage
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/random-promo/apply")
async def apply_random_promo(request: RandomPromoApplyRequest):
    """
    Applique les promos aléatoires sur Shopify.
    Utilise le même seed que le preview pour garantir les mêmes produits.
    """
    global apply_progress
    
    try:
        # Générer la même preview (avec le même seed si fourni)
        preview_request = RandomPromoRequest(
            countries=request.countries,
            catalog_percentage=request.catalog_percentage,
            min_discount=request.min_discount,
            max_discount=request.max_discount,
            seed=request.seed
        )
        
        preview_result = await preview_random_promo(preview_request)
        preview_data = preview_result["preview"]
        
        if request.dry_run:
            return {
                "applied": False,
                "dry_run": True,
                "would_update": len(preview_data),
                "summary": preview_result["summary"]
            }
        
        # Initialiser la progression
        apply_progress = {
            "active": True,
            "current_market": "Préparation promos...",
            "markets_done": 0,
            "total_markets": 0,
            "variants_updated": 0,
            "errors": []
        }
        
        # Grouper par pays
        updates_by_country = {}
        for item in preview_data:
            country = item["country"]
            if country not in updates_by_country:
                updates_by_country[country] = []
            updates_by_country[country].append({
                "variant_id": item["variant_id"],
                "price": item["new_price"],
                "compare_at_price": item["compare_at_price"]
            })
        
        apply_progress["total_markets"] = len(updates_by_country)
        
        results = {"success": [], "errors": [], "updated_count": 0}
        cache_updates = []
        
        for idx, (country, updates) in enumerate(updates_by_country.items()):
            apply_progress["current_market"] = country
            apply_progress["markets_done"] = idx
            
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    updated_count = update_result.get("updated", len(updates))
                    results["success"].append({
                        "country": country,
                        "updated": updated_count
                    })
                    results["updated_count"] += updated_count
                    apply_progress["variants_updated"] += updated_count
                    
                    # Préparer les mises à jour du cache
                    for update in updates:
                        cache_updates.append({
                            "market": country,
                            "variant_id": update["variant_id"],
                            "price": update["price"],
                            "compare_at_price": update["compare_at_price"]
                        })
                else:
                    error_msg = f"{country}: {update_result.get('error')}"
                    results["errors"].append(error_msg)
                    apply_progress["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"{country}: {str(e)}"
                results["errors"].append(error_msg)
                apply_progress["errors"].append(error_msg)
        
        # Mettre à jour le cache
        if cache_updates:
            cache_updated = price_cache.update_prices(cache_updates, save=True)
            results["cache_updated"] = cache_updated
        
        # Finaliser
        apply_progress["current_market"] = "Terminé"
        apply_progress["markets_done"] = len(updates_by_country)
        apply_progress["active"] = False
        
        log_operation("random_promo_apply", {
            "products_count": preview_result["summary"]["products_selected"],
            "catalog_percentage": request.catalog_percentage,
            "discount_range": f"{request.min_discount}%-{request.max_discount}%",
            "total_updates": results["updated_count"],
            "errors_count": len(results["errors"])
        })
        
        return {
            "applied": True,
            "summary": preview_result["summary"],
            "results": results
        }
    
    except Exception as e:
        apply_progress["active"] = False
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ANALYSE DE COHÉRENCE CROSS-MARCHÉS
# ========================================

class CoherenceAnalysisRequest(BaseModel):
    """Paramètres pour l'analyse de cohérence"""
    tolerance_percent: float = 15.0  # Tolérance de variation acceptable (%)
    reference_market: str = "France"  # Marché de référence pour les comparaisons


@router.post("/coherence/analyze")
async def analyze_price_coherence(request: CoherenceAnalysisRequest):
    """
    Analyse la cohérence des prix entre marchés.
    Détecte les anomalies où un même produit/variante a des prix incohérents
    par rapport au taux de change attendu.
    """
    from app.services.price_cache import price_cache
    import logging
    logger = logging.getLogger(__name__)

    if not price_cache.is_loaded or len(price_cache._cache) == 0:
        raise HTTPException(
            status_code=400,
            detail="Le cache des prix n'est pas chargé. Rafraîchissez le cache d'abord."
        )

    reference_market = request.reference_market
    if reference_market not in price_cache._cache:
        raise HTTPException(
            status_code=400,
            detail=f"Le marché de référence '{reference_market}' n'existe pas dans le cache."
        )

    logger.info(f"Analyzing price coherence with reference market: {reference_market}")

    # Récupérer les prix du marché de référence
    ref_market_data = price_cache._cache[reference_market]
    ref_prices = ref_market_data.get("prices", {})
    ref_currency = ref_market_data.get("currency", "EUR")

    anomalies = []
    stats = {
        "total_variants_analyzed": len(ref_prices),
        "total_comparisons": 0,
        "anomalies_found": 0,
        "markets_analyzed": [],
        "by_severity": {"critical": 0, "warning": 0, "minor": 0}
    }

    # Pour chaque marché, comparer avec le marché de référence
    for market_name, market_data in price_cache._cache.items():
        if market_name == reference_market:
            continue

        market_prices = market_data.get("prices", {})
        market_currency = market_data.get("currency", "EUR")
        market_config = COUNTRIES.get(market_name, {})
        expected_rate = market_config.get("exchange_rate", 1.0)

        stats["markets_analyzed"].append(market_name)

        for variant_id, ref_price_info in ref_prices.items():
            if variant_id not in market_prices:
                continue

            stats["total_comparisons"] += 1

            ref_price = float(ref_price_info.get("price", 0))
            market_price_info = market_prices[variant_id]
            market_price = float(market_price_info.get("price", 0))

            if ref_price <= 0 or market_price <= 0:
                continue

            # Prix attendu = prix de référence * taux de change
            expected_price = ref_price * expected_rate

            # Calculer l'écart
            if expected_price > 0:
                deviation_percent = abs((market_price - expected_price) / expected_price) * 100
            else:
                deviation_percent = 0

            # Si l'écart dépasse la tolérance, c'est une anomalie
            if deviation_percent > request.tolerance_percent:
                # Déterminer la sévérité
                if deviation_percent > 50:
                    severity = "critical"
                elif deviation_percent > 30:
                    severity = "warning"
                else:
                    severity = "minor"

                stats["anomalies_found"] += 1
                stats["by_severity"][severity] += 1

                anomalies.append({
                    "variant_id": variant_id,
                    "reference_market": reference_market,
                    "reference_price": ref_price,
                    "reference_currency": ref_currency,
                    "comparison_market": market_name,
                    "actual_price": market_price,
                    "expected_price": round(expected_price, 2),
                    "market_currency": market_currency,
                    "exchange_rate": expected_rate,
                    "deviation_percent": round(deviation_percent, 1),
                    "severity": severity,
                    "suggested_price": round(expected_price, 2)
                })

    # Trier les anomalies par sévérité et écart
    anomalies.sort(key=lambda x: (-{"critical": 3, "warning": 2, "minor": 1}[x["severity"]], -x["deviation_percent"]))

    logger.info(f"Coherence analysis complete: {stats['anomalies_found']} anomalies found")

    return {
        "stats": stats,
        "anomalies": anomalies[:500],  # Limiter à 500 pour l'affichage
        "reference_market": reference_market,
        "tolerance_percent": request.tolerance_percent
    }


@router.get("/coherence/markets")
async def get_available_markets_for_coherence():
    """Retourne les marchés disponibles pour l'analyse de cohérence"""
    from app.services.price_cache import price_cache

    if not price_cache.is_loaded:
        return {"markets": list(COUNTRIES.keys()), "source": "static"}

    markets = []
    for market_name, market_data in price_cache._cache.items():
        markets.append({
            "name": market_name,
            "currency": market_data.get("currency", "EUR"),
            "prices_count": len(market_data.get("prices", {}))
        })

    markets.sort(key=lambda x: x["name"])
    return {"markets": markets, "source": "cache"}


class CoherenceFixRequest(BaseModel):
    """Corrige les anomalies détectées"""
    anomaly_ids: List[str]  # Liste des variant_ids à corriger
    use_suggested_prices: bool = True


@router.post("/coherence/fix-preview")
async def preview_coherence_fix(request: CoherenceAnalysisRequest):
    """
    Prévisualise les corrections à appliquer pour toutes les anomalies détectées.
    """
    # D'abord analyser
    analysis = await analyze_price_coherence(request)

    # Préparer les corrections
    corrections = []
    for anomaly in analysis["anomalies"]:
        corrections.append({
            "variant_id": anomaly["variant_id"],
            "market": anomaly["comparison_market"],
            "current_price": anomaly["actual_price"],
            "suggested_price": anomaly["suggested_price"],
            "currency": anomaly["market_currency"],
            "deviation_percent": anomaly["deviation_percent"],
            "severity": anomaly["severity"]
        })

    return {
        "stats": analysis["stats"],
        "corrections": corrections,
        "reference_market": analysis["reference_market"]
    }


class CoherenceApplyRequest(BaseModel):
    """Appliquer les corrections de cohérence"""
    corrections: List[dict]  # Liste de {variant_id, market, suggested_price, currency}
    dry_run: bool = False


@router.post("/coherence/apply")
async def apply_coherence_corrections(request: CoherenceApplyRequest):
    """
    Applique les corrections de cohérence sur Shopify.
    Utilise les prix suggérés avec les terminaisons psychologiques appropriées.
    """
    global apply_progress
    import logging
    logger = logging.getLogger(__name__)

    if request.dry_run:
        return {
            "applied": False,
            "dry_run": True,
            "would_update": len(request.corrections),
            "corrections": request.corrections[:50]
        }

    # Initialiser la progression
    apply_progress = {
        "active": True,
        "current_market": "Préparation des corrections...",
        "markets_done": 0,
        "total_markets": 0,
        "variants_updated": 0,
        "errors": []
    }

    try:
        # Grouper les corrections par marché
        corrections_by_market = {}
        for correction in request.corrections:
            market = correction.get("market")
            if market not in corrections_by_market:
                corrections_by_market[market] = []

            # Appliquer la terminaison psychologique au prix suggéré
            suggested_price = float(correction.get("suggested_price", 0))
            final_price = apply_psychological_ending(suggested_price, market)

            # Calculer un compare_at basé sur le prix corrigé
            compare_at_raw = calculate_compare_at(final_price, 0.40)  # 40% de réduction affichée
            compare_at_price = apply_psychological_ending(compare_at_raw, market)

            corrections_by_market[market].append({
                "variant_id": correction.get("variant_id"),
                "price": final_price,
                "compare_at_price": compare_at_price
            })

        apply_progress["total_markets"] = len(corrections_by_market)
        logger.info(f"Applying corrections to {len(corrections_by_market)} markets")

        results = {"success": [], "errors": [], "updated_count": 0}
        cache_updates = []

        for idx, (market, corrections) in enumerate(corrections_by_market.items()):
            apply_progress["current_market"] = market
            apply_progress["markets_done"] = idx

            try:
                update_result = await shopify_service.bulk_update_prices(market, corrections)

                if update_result.get("success"):
                    updated_count = update_result.get("updated", len(corrections))
                    results["success"].append({
                        "market": market,
                        "updated": updated_count
                    })
                    results["updated_count"] += updated_count
                    apply_progress["variants_updated"] += updated_count

                    # Préparer les mises à jour du cache
                    for corr in corrections:
                        cache_updates.append({
                            "market": market,
                            "variant_id": corr["variant_id"],
                            "price": corr["price"],
                            "compare_at_price": corr["compare_at_price"]
                        })
                else:
                    error_msg = f"{market}: {update_result.get('error')}"
                    results["errors"].append(error_msg)
                    apply_progress["errors"].append(error_msg)

            except Exception as e:
                error_msg = f"{market}: {str(e)}"
                results["errors"].append(error_msg)
                apply_progress["errors"].append(error_msg)
                logger.error(f"Error applying corrections to {market}: {e}")

        # Mettre à jour le cache
        if cache_updates:
            cache_updated = price_cache.update_prices(cache_updates, save=True)
            results["cache_updated"] = cache_updated

        # Finaliser
        apply_progress["current_market"] = "Terminé"
        apply_progress["markets_done"] = len(corrections_by_market)
        apply_progress["active"] = False

        log_operation("coherence_fix_apply", {
            "markets_count": len(corrections_by_market),
            "total_corrections": len(request.corrections),
            "updated_count": results["updated_count"],
            "errors_count": len(results["errors"])
        })

        return {
            "applied": True,
            "results": results
        }

    except Exception as e:
        apply_progress["active"] = False
        logger.error(f"Coherence fix failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
