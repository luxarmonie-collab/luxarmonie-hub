"""
Router pour les opérations de pricing
C'est le cœur du Luxarmonie Pricing Manager
V2 - Avec récupération des prix réels par marché via PriceLists
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.services.pricing_engine import pricing_engine, PricingOperation
from app.config.countries import COUNTRIES, get_all_countries
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


# ========================================
# MODELS
# ========================================

class PricingPreviewRequest(BaseModel):
    countries: List[str]
    product_ids: Optional[List[str]] = None
    variant_ids: Optional[List[str]] = None  # NEW: variantes spécifiques
    base_adjustment: float = -0.12
    apply_vat: bool = True
    discount: float = 0.40


class PricingApplyRequest(BaseModel):
    countries: List[str]
    product_ids: Optional[List[str]] = None
    variant_ids: Optional[List[str]] = None  # NEW: variantes spécifiques
    base_adjustment: float = -0.12
    apply_vat: bool = True
    discount: float = 0.40
    dry_run: bool = False


class SingleProductPricingRequest(BaseModel):
    sku: str
    base_price_eur: float
    countries: List[str]
    discount: float = 0.40


class ExchangeRatesUpdate(BaseModel):
    rates: dict


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
    """Configuration actuelle du pricing"""
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
        ]
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
    V2: Récupère les vrais prix actuels par marché via PriceLists
    """
    try:
        countries = get_all_countries() if "all" in request.countries else request.countries
        
        # Récupérer les produits et leurs variantes
        variants_data = []  # {variant_id, sku, title, base_price, product_title}
        
        if request.product_ids:
            for pid in request.product_ids:
                product = await shopify_service.get_product_by_id(pid)
                if product:
                    for variant in product["variants"]:
                        variant_id = variant.get("id") or variant.get("admin_graphql_api_id")
                        
                        # Si variant_ids spécifiés, filtrer
                        if request.variant_ids and variant_id not in request.variant_ids:
                            continue
                        
                        variants_data.append({
                            "variant_id": variant_id,
                            "sku": variant["sku"],
                            "title": f"{product['title']} - {variant['title']}",
                            "product_title": product['title'],
                            "variant_title": variant['title'],
                            "base_price": float(variant["price"])
                        })
        else:
            raw_products = await shopify_service.search_products("", 100)
            for product in raw_products:
                for variant in product["variants"]:
                    variant_id = variant.get("id") or variant.get("admin_graphql_api_id")
                    
                    if request.variant_ids and variant_id not in request.variant_ids:
                        continue
                    
                    variants_data.append({
                        "variant_id": variant_id,
                        "sku": variant["sku"],
                        "title": f"{product['title']} - {variant['title']}",
                        "product_title": product['title'],
                        "variant_title": variant['title'],
                        "base_price": float(variant["price"])
                    })
        
        if not variants_data:
            return {
                "summary": {"total_products": 0, "total_countries": 0, "total_updates": 0},
                "preview": []
            }
        
        # Extraire tous les variant_ids
        all_variant_ids = [v["variant_id"] for v in variants_data if v["variant_id"]]
        
        # ========================================
        # NOUVEAU: Récupérer les vrais prix par marché
        # ========================================
        market_prices = {}
        
        try:
            # Récupérer les prix de toutes les variantes pour tous les marchés sélectionnés
            market_prices = await shopify_service.get_variant_prices_by_market(
                variant_ids=all_variant_ids,
                market_ids=countries  # Les noms de marchés
            )
        except Exception as e:
            print(f"Warning: Could not fetch market prices: {e}")
            # Continue avec les prix de base si erreur
        
        # ========================================
        # Construire la prévisualisation
        # ========================================
        operation = PricingOperation(
            base_adjustment=request.base_adjustment,
            apply_vat=request.apply_vat,
            compare_at_markup=request.discount
        )
        
        preview = []
        
        for variant in variants_data:
            variant_id = variant["variant_id"]
            
            for country in countries:
                # Récupérer le prix actuel du marché (si disponible)
                current_price = None
                current_compare_at = None
                current_currency = None
                
                if country in market_prices:
                    market_data = market_prices[country]
                    current_currency = market_data.get("currency")
                    
                    # Chercher le prix de cette variante
                    prices = market_data.get("prices", {})
                    if variant_id in prices:
                        price_info = prices[variant_id]
                        current_price = float(price_info.get("price", 0)) if price_info.get("price") else None
                        current_compare_at = float(price_info.get("compareAtPrice", 0)) if price_info.get("compareAtPrice") else None
                
                # Calculer le nouveau prix
                calc = pricing_engine.calculate_price(variant["base_price"], country, operation)
                
                if calc:
                    preview.append({
                        "sku": variant["sku"],
                        "title": variant["title"],
                        "product_title": variant["product_title"],
                        "variant_title": variant["variant_title"],
                        "variant_id": variant_id,
                        "country": country,
                        "currency": calc.currency,
                        # Prix actuels (du marché)
                        "current_price": current_price,
                        "current_compare_at": current_compare_at,
                        "current_currency": current_currency or calc.currency,
                        # Nouveaux prix calculés
                        "new_price": calc.final_price,
                        "compare_at_price": calc.compare_at_price,
                        "discount_percentage": calc.discount_percentage,
                        # Prix de base (référence)
                        "base_price_eur": variant["base_price"]
                    })
        
        return {
            "summary": {
                "total_products": len(variants_data),
                "total_countries": len(countries),
                "total_updates": len(preview)
            },
            "preview": preview[:500]  # Augmenté à 500 pour plus de visibilité
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_pricing(request: PricingApplyRequest):
    """
    Applique les changements de prix sur Shopify
    V2: Support des variant_ids spécifiques
    """
    try:
        countries = get_all_countries() if "all" in request.countries else request.countries
        
        # D'abord, générer la preview pour avoir les prix calculés
        preview_request = PricingPreviewRequest(
            countries=request.countries,
            product_ids=request.product_ids,
            variant_ids=request.variant_ids,
            base_adjustment=request.base_adjustment,
            apply_vat=request.apply_vat,
            discount=request.discount
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
            config = COUNTRIES.get(country)
            if not config:
                results["errors"].append(f"Config not found for {country}")
                continue
            
            # Appeler Shopify pour mettre à jour
            try:
                update_result = await shopify_service.bulk_update_prices(country, updates)
                
                if update_result.get("success"):
                    results["success"].append({
                        "country": country,
                        "updated": len(updates)
                    })
                    results["updated_count"] += len(updates)
                else:
                    results["errors"].append(f"{country}: {update_result.get('error')}")
            except Exception as e:
                results["errors"].append(f"{country}: {str(e)}")
        
        log_operation("pricing_apply", {
            "countries": countries,
            "variant_count": len(request.variant_ids) if request.variant_ids else "all",
            "product_count": len(request.product_ids) if request.product_ids else "all",
            "results": results
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
        "operations": pricing_history[-20:]  # 20 dernières
    }
