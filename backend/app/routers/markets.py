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
                # Leo 2026-08-17 : certains marchés Shopify renvoient currencySettings=null
                # (clé présente mais valeur None) -> le défaut de .get() ne s'applique pas et
                # le chaînage levait "'NoneType' object has no attribute 'get'".
                # Résultat : GET /api/markets/ répondait 500 sur TOUT le catalogue, donc plus
                # aucun moyen de comparer devise config vs devise price list depuis l'API.
                "shopifyCurrency": (
                    (market.get("currencySettings") or {}).get("baseCurrency") or {}
                ).get("currencyCode"),
                "priceListCurrency": (market.get("priceList") or {}).get("currency"),
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


@router.get("/currency-check")
async def currency_check():
    """
    Contrôle read-only : compare, marché par marché, la devise déclarée dans
    countries.py à la devise réelle de la price list Shopify.

    Aucune écriture. Sert à savoir AVANT un apply quels marchés sont bloqués par
    le garde-fou devise de shopify_service.bulk_update_prices.

    Trois familles remontées :
      - blocked      : devise config != devise price list -> écriture refusée
      - unreachable  : marché configuré sans catalog/price list live -> apply sans effet
      - ok           : les deux devises concordent
    """
    try:
        markets = await shopify_service.get_all_markets()

        live_names = set()
        blocked, ok = [], []

        for market in markets:
            name = market.get("name")
            live_names.add(name)
            price_list = market.get("priceList") or {}
            list_currency = price_list.get("currency")
            config = COUNTRIES.get(name)

            if not config or not list_currency:
                continue

            entry = {
                "market": name,
                "config_currency": config.get("currency"),
                "price_list_currency": list_currency,
                "exchange_rate": config.get("exchange_rate"),
            }
            if config.get("currency") != list_currency:
                entry["impact"] = (
                    f"un apply écrirait base x{config.get('exchange_rate')} "
                    f"sous un libellé {list_currency}"
                )
                blocked.append(entry)
            else:
                ok.append(entry)

        unreachable = [
            {"market": name, "config_currency": cfg.get("currency"),
             "reason": "aucun catalog/price list live à ce nom exact — apply sans effet"}
            for name, cfg in COUNTRIES.items() if name not in live_names
        ]

        return {
            "success": True,
            "summary": {
                "markets_live": len(live_names),
                "configured": len(COUNTRIES),
                "ok": len(ok),
                "blocked": len(blocked),
                "unreachable": len(unreachable),
            },
            "blocked": blocked,
            "unreachable": unreachable,
            "ok": [e["market"] for e in ok],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        # Price list - utiliser la priceList déjà présente dans le market
        price_list = market.get("priceList")

        return {
            "market": market,
            "config": config,
            "priceList": {
                "id": price_list["id"] if price_list else None,
                "currency": price_list["currency"] if price_list else None,
                "name": price_list.get("name") if price_list else None
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
