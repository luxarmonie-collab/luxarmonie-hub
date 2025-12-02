"""
Router pour les opérations de pricing
C'est le cœur du Luxarmonie Pricing Manager
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
    base_adjustment: float = -0.12
    apply_vat: bool = True
    discount: float = 0.40


class PricingApplyRequest(BaseModel):
    countries: List[str]
    product_ids: Optional[List[str]] = None
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
    """Prévisualise les changements de prix"""
    try:
        countries = get_all_countries() if "all" in request.countries else request.countries
        
        # Récupérer les produits
        if request.product_ids:
            products = []
            for pid in request.product_ids:
                product = await shopify_service.get_product_by_id(pid)
                if product:
                    for variant in product["variants"]:
                        products.append({
                            "sku": variant["sku"],
                            "title": f"{product['title']} - {variant['title']}",
                            "price": float(variant["price"])
                        })
        else:
            raw_products = await shopify_service.search_products("", 100)
            products = []
            for product in raw_products:
                for variant in product["variants"]:
                    products.append({
                        "sku": variant["sku"],
                        "title": f"{product['title']} - {variant['title']}",
                        "price": float(variant["price"])
                    })
        
        operation = PricingOperation(
            base_adjustment=request.base_adjustment,
            apply_vat=request.apply_vat,
            compare_at_markup=request.discount
        )
        
        preview = pricing_engine.preview_bulk_update(products, countries, operation)
        
        return {
            "summary": {
                "total_products": preview["total_products"],
                "total_countries": preview["total_countries"],
                "total_updates": preview["total_updates"]
            },
            "preview": preview["preview"][:200]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_pricing(request: PricingApplyRequest):
    """Applique les changements de prix sur Shopify"""
    try:
        countries = get_all_countries() if "all" in request.countries else request.countries
        
        results = {"success": [], "errors": []}
        
        for country in countries:
            config = COUNTRIES.get(country)
            if not config:
                results["errors"].append(f"Config not found for {country}")
                continue
            
            # Appeler Shopify pour mettre à jour
            update_result = await shopify_service.bulk_update_prices(country, [])
            
            if update_result.get("success"):
                results["success"].append(country)
            else:
                results["errors"].append(f"{country}: {update_result.get('error')}")
        
        log_operation("pricing_apply", {
            "countries": countries,
            "product_count": len(request.product_ids) if request.product_ids else "all",
            "results": results
        })
        
        return {
            "applied": not request.dry_run,
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """Récupère l'historique des opérations"""
    return {
        "total": len(pricing_history),
        "operations": pricing_history[-20:]  # 20 dernières
    }
