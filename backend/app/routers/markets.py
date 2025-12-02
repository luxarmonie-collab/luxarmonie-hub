"""
Router pour la gestion des marchés Shopify
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.config.countries import COUNTRIES, get_all_countries
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()


class MarketConfig(BaseModel):
    """Configuration d'un marché"""
    name: str
    currency: str
    ending: str
    vat: float
    exchange_rate: float
    adjustment: str
    culture: str


class ExchangeRateUpdate(BaseModel):
    """Mise à jour d'un taux de change"""
    country: str
    rate: float


class VatUpdate(BaseModel):
    """Mise à jour d'une TVA"""
    country: str
    vat: float


@router.get("/")
async def get_markets():
    """
    Récupère tous les marchés Shopify avec leurs configs Luxarmonie
    """
    try:
        # Récupérer les marchés depuis Shopify
        shopify_markets = await shopify_service.get_all_markets()
        
        # Enrichir avec les configs Luxarmonie
        result = []
        for market in shopify_markets:
            market_name = market["name"]
            config = COUNTRIES.get(market_name, None)
            
            result.append({
                "id": market["id"],
                "numericId": market["numericId"],
                "name": market_name,
                "handle": market.get("handle"),
                "enabled": market.get("enabled", True),
                "primary": market.get("primary", False),
                "shopifyCurrency": market.get("currencySettings", {}).get("baseCurrency", {}).get("currencyCode"),
                "config": {
                    "currency": config["currency"] if config else None,
                    "ending": config["ending"] if config else "99",
                    "vat": config["vat"] if config else 0,
                    "exchange_rate": config["exchange_rate"] if config else 1,
                    "adjustment": config["adjustment"] if config else "minus_10",
                    "culture": config["culture"] if config else "low-context"
                } if config else None,
                "hasConfig": config is not None
            })
        
        return {
            "total": len(result),
            "configured": len([m for m in result if m["hasConfig"]]),
            "markets": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/countries")
async def get_countries_config():
    """
    Récupère toutes les configurations pays (pour référence)
    """
    countries = []
    for name, config in COUNTRIES.items():
        countries.append({
            "name": name,
            **config
        })
    
    return {
        "total": len(countries),
        "countries": countries
    }


@router.get("/{market_name}")
async def get_market_details(market_name: str):
    """
    Récupère les détails d'un marché spécifique
    """
    try:
        # Récupérer depuis Shopify
        markets = await shopify_service.get_all_markets()
        market = next((m for m in markets if m["name"] == market_name), None)
        
        if not market:
            raise HTTPException(status_code=404, detail=f"Market '{market_name}' not found")
        
        # Config Luxarmonie
        config = COUNTRIES.get(market_name)
        
        # Price list
        price_list = await shopify_service.get_catalog_price_list(market["id"])
        
        return {
            "market": market,
            "config": config,
            "priceList": {
                "id": price_list["id"] if price_list else None,
                "currency": price_list["currency"] if price_list else None,
                "pricesCount": len(price_list["prices"]["edges"]) if price_list else 0
            } if price_list else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/exchange-rate")
async def update_exchange_rate(update: ExchangeRateUpdate):
    """
    Met à jour le taux de change d'un pays (temporaire, en mémoire)
    """
    if update.country not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Country '{update.country}' not found")
    
    # Note: Cette modification est en mémoire uniquement
    # Pour persister, il faudrait une base de données
    COUNTRIES[update.country]["exchange_rate"] = update.rate
    
    return {
        "success": True,
        "country": update.country,
        "new_rate": update.rate
    }


@router.put("/vat")
async def update_vat(update: VatUpdate):
    """
    Met à jour la TVA d'un pays (temporaire, en mémoire)
    """
    if update.country not in COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Country '{update.country}' not found")
    
    COUNTRIES[update.country]["vat"] = update.vat
    
    return {
        "success": True,
        "country": update.country,
        "new_vat": update.vat
    }
