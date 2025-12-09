"""
Router pour les opérations de pricing
V3 - Calcul basé sur prix ACTUEL du marché + tous les produits
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.services.pricing_engine import pricing_engine, PricingOperation
from app.config.countries import COUNTRIES, get_all_countries
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import math

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


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
    Utilise le cache si chargé, sinon Shopify, sinon config statique
    """
    from app.services.price_cache import price_cache
    
    # 1. Si le cache est chargé, utiliser les marchés du cache
    if price_cache.is_loaded:
        print("CONFIG: Using cache for markets list")
        countries = []
        for market_name, market_data in price_cache._cache.items():
            currency = market_data.get("currency", "EUR")
            config = COUNTRIES.get(market_name, {})
            countries.append({
                "name": market_name,
                "currency": currency,
                "ending": config.get("ending", 0.99),
                "vat": config.get("vat", 0),
                "exchange_rate": config.get("exchange_rate", 1),
                "adjustment": config.get("adjustment", "none"),
                "prices_count": len(market_data.get("prices", {}))
            })
        countries.sort(key=lambda x: x["name"])
        return {"countries": countries, "source": "cache"}
    
    # 2. Toujours essayer Shopify (même pendant le chargement du cache)
    print("CONFIG: Cache not loaded, fetching from Shopify...")
    try:
        markets = await shopify_service.get_all_markets()
        print(f"CONFIG: Got {len(markets)} markets from Shopify")
        
        countries = []
        for market in markets:
            market_name = market["name"]
            price_list = market.get("priceList")
            currency = price_list["currency"] if price_list else "EUR"
            config = COUNTRIES.get(market_name, {})
            countries.append({
                "name": market_name,
                "currency": currency,
                "ending": config.get("ending", 0.99),
                "vat": config.get("vat", 0),
                "exchange_rate": config.get("exchange_rate", 1),
                "adjustment": config.get("adjustment", "none")
            })
        countries.sort(key=lambda x: x["name"])
        print(f"CONFIG: Returning {len(countries)} countries from Shopify")
        return {"countries": countries, "source": "shopify"}
    except Exception as e:
        print(f"CONFIG ERROR: Failed to load from Shopify: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Fallback sur config statique (ne devrait jamais arriver)
    print(f"CONFIG: Using static fallback with {len(COUNTRIES)} countries")
    return {
        "countries": [
            {
                "name": name,
                "currency": config["currency"],
                "ending": config["ending"],
                "vat": config["vat"],
                "exchange_rate": config["exchange_rate"],
                "adjustment": config["adjustment"]
            }
            for name, config in COUNTRIES.items()
        ],
        "source": "static"
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
    V3: Support tous produits + calcul sur prix marché
    """
    try:
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
        
        results = {"success": [], "errors": [], "updated_count": 0}
        
        for country, updates in updates_by_country.items():
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    results["success"].append({
                        "country": country,
                        "updated": update_result.get("updated", len(updates))
                    })
                    results["updated_count"] += update_result.get("updated", 0)
                else:
                    results["errors"].append(f"{country}: {update_result.get('error')}")
                    if update_result.get("errors"):
                        for err in update_result["errors"]:
                            results["errors"].append(f"{country}: {err}")
                            
            except Exception as e:
                results["errors"].append(f"{country}: {str(e)}")
        
        log_operation("pricing_apply", {
            "countries": list(updates_by_country.keys()),
            "total_updates": results["updated_count"],
            "errors_count": len(results["errors"])
        })
        
        return {
            "applied": True,
            "results": results
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """Récupère l'historique des opérations"""
    return {
        "total": len(pricing_history),
        "operations": pricing_history[-20:]
    }
