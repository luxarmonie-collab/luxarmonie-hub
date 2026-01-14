"""
Router pour la correction de prix individuels
- Mode "Prix fixe" : définir un prix EUR et recalculer tous les marchés
- Mode "Copier variante" : copier les prix d'une variante modèle vers d'autres
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.services.price_cache import price_cache
from app.config.countries import COUNTRIES
from typing import List, Optional, Dict
from pydantic import BaseModel
import math

router = APIRouter(prefix="/api/fix-price", tags=["fix-price"])


# ========================================
# MODELS
# ========================================

class FixPriceRequest(BaseModel):
    """Définir un prix fixe pour des variantes"""
    variant_ids: List[str]
    base_price_eur: float  # Prix de référence en EUR
    compare_at_price_eur: Optional[float] = None  # Compare at en EUR (optionnel)
    countries: List[str] = ["all"]  # Marchés à modifier


class FixPriceApplyRequest(FixPriceRequest):
    """Appliquer les prix fixes"""
    dry_run: bool = False


class CopyVariantRequest(BaseModel):
    """Copier les prix d'une variante source"""
    source_variant_id: str
    target_variant_ids: List[str]
    countries: List[str] = ["all"]


class CopyVariantApplyRequest(CopyVariantRequest):
    """Appliquer la copie"""
    dry_run: bool = False


# ========================================
# FONCTIONS DE TERMINAISON
# ========================================

def round_99(price: float) -> float:
    return float(math.floor(price)) + 0.99

def round_95(price: float) -> float:
    return float(math.floor(price)) + 0.95

def round_00(price: float) -> float:
    return float(round(price))

def round_9_int(price: float) -> float:
    base = int(price)
    last = base % 10
    if last == 9:
        return float(base)
    elif last < 9:
        return float(base - last + 9) if base >= 10 else float(9)
    return float(base - 1)

def round_000(price: float) -> float:
    thousands = round(price / 1000)
    return float(max(thousands, 1) * 1000)

def round_990(price: float) -> float:
    base = int(price)
    if base >= 10000:
        return float((base // 1000) * 1000 + 990)
    elif base >= 1000:
        return float((base // 100) * 100 + 90)
    else:
        return float((base // 10) * 10 + 9)

def round_kr(price: float) -> float:
    return float(round(price / 5) * 5)


COUNTRY_ROUNDING = {
    # .99
    'France': round_99, 'USA': round_99, 'UK': round_99, 'Canada': round_99,
    'Australie': round_99, 'Belgique': round_99, 'Espagne': round_99,
    'Pays-Bas': round_99, 'Luxembourg': round_99, 'ESTONIE': round_99,
    'Grèce': round_99, 'Irlande': round_99, 'Portugal': round_99,
    'Croatie': round_99, 'Finlande': round_99, 'Pologne': round_99,
    'Mexique': round_99, 'Israël': round_99, 'Pérou': round_99,
    'Bolivie': round_99, 'Guatemala': round_99, 'Honduras': round_99,
    'Turquie': round_99, 'Nouvelle Zélande': round_99,
    
    # .95
    'Allemagne': round_95, 'Autriche': round_95, 'Suisse': round_95,
    
    # .00
    'Italie': round_00, 'Brésil': round_00, 'Hong Kong': round_00,
    'Honk Hong': round_00, 'SINGAPOUR': round_00, 'Argentine': round_00,
    'Norvège': round_00, 'Uruguay': round_00, 'Costa Rica': round_00,
    'Afrique du Sud': round_00, 'Équateur': round_00, 'Bahreïn': round_00,
    'Panama': round_00, 'Salvador': round_00, 'Malaisie': round_00,
    
    # Scandinave
    'Danemark': round_kr, 'Suède': round_kr,
    
    # 990
    'Hongrie': round_990, 'République tchèque': round_990, 'Serbie': round_990,
    
    # 9 entier
    'Arabie Saoudite': round_9_int, 'Émirats Arabes Unis': round_9_int, 'Qatar': round_9_int,
    
    # Milliers
    'Chili': round_000, 'Colombie': round_000, 'Paraguay': round_000,
}


def get_exchange_rate(country: str) -> float:
    """Récupère le taux de change pour un pays"""
    config = COUNTRIES.get(country, {})
    return config.get("exchange_rate", 1.0)


def get_currency(country: str) -> str:
    """Récupère la devise pour un pays"""
    config = COUNTRIES.get(country, {})
    return config.get("currency", "EUR")


def calculate_price_for_country(base_price_eur: float, country: str) -> float:
    """
    Calcule le prix pour un pays donné à partir d'un prix EUR de référence.
    Applique: taux de change + terminaison psychologique
    """
    exchange_rate = get_exchange_rate(country)
    converted = base_price_eur * exchange_rate
    
    # Appliquer la terminaison psychologique
    round_func = COUNTRY_ROUNDING.get(country, round_99)
    return round_func(converted)


def format_price(price: float, country: str) -> str:
    """Formate le prix selon le pays"""
    config = COUNTRIES.get(country, {})
    currency = config.get("currency", "EUR")
    
    no_decimal = ["HUF", "CZK", "RSD", "CLP", "COP", "PYG", "SAR", "QAR", "AED", "DKK", "SEK", "NOK", "HKD", "CRC", "UYU", "DOP"]
    
    if currency in no_decimal:
        return str(int(price))
    return f"{price:.2f}"


# ========================================
# ENDPOINTS - PRIX FIXE
# ========================================

@router.post("/preview")
async def preview_fix_price(request: FixPriceRequest):
    """
    Prévisualise la modification de prix fixe.
    Calcule les nouveaux prix pour tous les marchés à partir du prix EUR de référence.
    """
    try:
        # Déterminer les marchés
        if 'all' in request.countries:
            countries = price_cache.get_all_markets()
        else:
            countries = request.countries
        
        if not countries:
            countries = list(COUNTRIES.keys())
        
        preview_items = []
        
        # Récupérer les infos des variantes
        variants_info = {}
        for variant_id in request.variant_ids:
            # Chercher dans le cache pour avoir le titre
            for country in countries:
                cached = price_cache.get_price(country, variant_id)
                if cached:
                    variants_info[variant_id] = {
                        "title": cached.get("title", f"Variant {variant_id}"),
                        "product_title": cached.get("product_title", "")
                    }
                    break
            
            if variant_id not in variants_info:
                variants_info[variant_id] = {
                    "title": f"Variant {variant_id}",
                    "product_title": ""
                }
        
        # Calculer les prix pour chaque variante et chaque marché
        for variant_id in request.variant_ids:
            for country in countries:
                # Prix actuel
                cached = price_cache.get_price(country, variant_id)
                current_price = float(cached.get("price", 0)) if cached else None
                current_compare_at = float(cached.get("compare_at_price", 0)) if cached and cached.get("compare_at_price") else None
                currency = get_currency(country)
                
                # Nouveaux prix calculés
                new_price = calculate_price_for_country(request.base_price_eur, country)
                
                if request.compare_at_price_eur:
                    new_compare_at = calculate_price_for_country(request.compare_at_price_eur, country)
                else:
                    new_compare_at = None
                
                # Calculer la différence
                price_diff = None
                if current_price and current_price > 0:
                    price_diff = round(((new_price - current_price) / current_price) * 100, 1)
                
                preview_items.append({
                    "variant_id": variant_id,
                    "variant_title": variants_info[variant_id]["title"],
                    "product_title": variants_info[variant_id]["product_title"],
                    "country": country,
                    "currency": currency,
                    "current_price": format_price(current_price, country) if current_price else None,
                    "current_compare_at": format_price(current_compare_at, country) if current_compare_at else None,
                    "new_price": format_price(new_price, country),
                    "new_compare_at": format_price(new_compare_at, country) if new_compare_at else None,
                    "price_diff_percent": price_diff
                })
        
        return {
            "success": True,
            "summary": {
                "variants_count": len(request.variant_ids),
                "countries_count": len(countries),
                "total_updates": len(preview_items),
                "base_price_eur": request.base_price_eur,
                "compare_at_price_eur": request.compare_at_price_eur
            },
            "preview": preview_items
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_fix_price(request: FixPriceApplyRequest):
    """
    Applique les prix fixes sur Shopify.
    """
    try:
        # D'abord générer la preview
        preview_result = await preview_fix_price(request)
        preview_items = preview_result["preview"]
        
        if request.dry_run:
            return {
                "applied": False,
                "dry_run": True,
                "would_update": len(preview_items),
                "summary": preview_result["summary"]
            }
        
        # Grouper par pays
        updates_by_country = {}
        for item in preview_items:
            country = item["country"]
            if country not in updates_by_country:
                updates_by_country[country] = []
            
            update_data = {
                "variant_id": item["variant_id"],
                "price": item["new_price"]
            }
            if item["new_compare_at"]:
                update_data["compare_at_price"] = item["new_compare_at"]
            
            updates_by_country[country].append(update_data)
        
        results = {"success": [], "errors": [], "updated_count": 0}
        cache_updates = []
        
        for country, updates in updates_by_country.items():
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    updated_count = update_result.get("updated", len(updates))
                    results["success"].append({
                        "country": country,
                        "updated": updated_count
                    })
                    results["updated_count"] += updated_count
                    
                    # Préparer les mises à jour du cache
                    for update in updates:
                        cache_updates.append({
                            "market": country,
                            "variant_id": update["variant_id"],
                            "price": update["price"],
                            "compare_at_price": update.get("compare_at_price")
                        })
                else:
                    error_msg = f"{country}: {update_result.get('error')}"
                    results["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"{country}: {str(e)}"
                results["errors"].append(error_msg)
        
        # Mettre à jour le cache
        if cache_updates:
            cache_updated = price_cache.update_prices(cache_updates, save=True)
            results["cache_updated"] = cache_updated
        
        return {
            "applied": True,
            "summary": preview_result["summary"],
            "results": results
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ENDPOINTS - COPIER VARIANTE
# ========================================

@router.post("/copy/preview")
async def preview_copy_variant(request: CopyVariantRequest):
    """
    Prévisualise la copie des prix d'une variante source vers d'autres variantes.
    """
    try:
        # Déterminer les marchés
        if 'all' in request.countries:
            countries = price_cache.get_all_markets()
        else:
            countries = request.countries
        
        if not countries:
            countries = list(COUNTRIES.keys())
        
        # Récupérer les prix de la variante source
        source_prices = {}
        source_info = {"title": f"Variant {request.source_variant_id}", "product_title": ""}
        
        for country in countries:
            cached = price_cache.get_price(country, request.source_variant_id)
            if cached:
                source_prices[country] = {
                    "price": cached.get("price"),
                    "compare_at_price": cached.get("compare_at_price"),
                    "currency": cached.get("currency", get_currency(country))
                }
                source_info["title"] = cached.get("title", source_info["title"])
                source_info["product_title"] = cached.get("product_title", "")
        
        if not source_prices:
            raise HTTPException(
                status_code=404, 
                detail=f"Aucun prix trouvé pour la variante source {request.source_variant_id}"
            )
        
        preview_items = []
        
        # Pour chaque variante cible
        for target_variant_id in request.target_variant_ids:
            if target_variant_id == request.source_variant_id:
                continue  # Skip si c'est la même variante
            
            # Récupérer les infos de la variante cible
            target_info = {"title": f"Variant {target_variant_id}", "product_title": ""}
            for country in countries:
                cached = price_cache.get_price(country, target_variant_id)
                if cached:
                    target_info["title"] = cached.get("title", target_info["title"])
                    target_info["product_title"] = cached.get("product_title", "")
                    break
            
            # Copier les prix pour chaque marché
            for country in countries:
                if country not in source_prices:
                    continue
                
                source = source_prices[country]
                currency = source["currency"]
                
                # Prix actuel de la cible
                target_cached = price_cache.get_price(country, target_variant_id)
                current_price = float(target_cached.get("price", 0)) if target_cached else None
                current_compare_at = float(target_cached.get("compare_at_price", 0)) if target_cached and target_cached.get("compare_at_price") else None
                
                preview_items.append({
                    "source_variant_id": request.source_variant_id,
                    "source_title": source_info["title"],
                    "target_variant_id": target_variant_id,
                    "target_title": target_info["title"],
                    "product_title": target_info["product_title"],
                    "country": country,
                    "currency": currency,
                    "current_price": format_price(current_price, country) if current_price else None,
                    "new_price": source["price"],
                    "new_compare_at": source["compare_at_price"]
                })
        
        return {
            "success": True,
            "summary": {
                "source_variant_id": request.source_variant_id,
                "source_title": source_info["title"],
                "target_variants_count": len(request.target_variant_ids),
                "countries_count": len(source_prices),
                "total_updates": len(preview_items)
            },
            "source_prices": source_prices,
            "preview": preview_items
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/copy/apply")
async def apply_copy_variant(request: CopyVariantApplyRequest):
    """
    Applique la copie des prix sur Shopify.
    """
    try:
        # D'abord générer la preview
        preview_result = await preview_copy_variant(request)
        preview_items = preview_result["preview"]
        
        if request.dry_run:
            return {
                "applied": False,
                "dry_run": True,
                "would_update": len(preview_items),
                "summary": preview_result["summary"]
            }
        
        # Grouper par pays
        updates_by_country = {}
        for item in preview_items:
            country = item["country"]
            if country not in updates_by_country:
                updates_by_country[country] = []
            
            update_data = {
                "variant_id": item["target_variant_id"],
                "price": item["new_price"]
            }
            if item["new_compare_at"]:
                update_data["compare_at_price"] = item["new_compare_at"]
            
            updates_by_country[country].append(update_data)
        
        results = {"success": [], "errors": [], "updated_count": 0}
        cache_updates = []
        
        for country, updates in updates_by_country.items():
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    updated_count = update_result.get("updated", len(updates))
                    results["success"].append({
                        "country": country,
                        "updated": updated_count
                    })
                    results["updated_count"] += updated_count
                    
                    # Préparer les mises à jour du cache
                    for update in updates:
                        cache_updates.append({
                            "market": country,
                            "variant_id": update["variant_id"],
                            "price": update["price"],
                            "compare_at_price": update.get("compare_at_price")
                        })
                else:
                    error_msg = f"{country}: {update_result.get('error')}"
                    results["errors"].append(error_msg)
                    
            except Exception as e:
                error_msg = f"{country}: {str(e)}"
                results["errors"].append(error_msg)
        
        # Mettre à jour le cache
        if cache_updates:
            cache_updated = price_cache.update_prices(cache_updates, save=True)
            results["cache_updated"] = cache_updated
        
        return {
            "applied": True,
            "summary": preview_result["summary"],
            "results": results
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ENDPOINT INFO
# ========================================

@router.get("/info")
async def get_fix_price_info():
    """Infos sur le module de correction de prix"""
    return {
        "module": "Fix Price",
        "features": [
            "Définir un prix fixe EUR et recalculer tous les marchés",
            "Copier les prix d'une variante modèle vers d'autres",
            "Terminaisons psychologiques automatiques",
            "Prévisualisation avant application"
        ],
        "supported_countries": len(COUNTRIES)
    }
