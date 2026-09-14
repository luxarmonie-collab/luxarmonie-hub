"""
Router pour la gestion des marchés Shopify
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.config.countries import (
    COUNTRIES,
    _fold,
    get_all_countries,
    suggest_country_names,
)
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

        # ── unreachable : pays configuré sans marché live au MÊME nom exact ──
        # Le chemin d'écriture (shopify_service.bulk_update_prices) cherche le
        # marché par égalité stricte de nom. Un écart d'une lettre = apply sans
        # effet, en silence : "Market 'X' not found" n'est remonté qu'au niveau
        # d'un apply, jamais avant.
        #
        # Leo 2026-09-14 — on ajoute la RAISON probable, parce que les 3 cas
        # mesurés sur la prod sont tous des désalignements de libellé, pas des
        # marchés manquants :
        #     countries.py                 marché live Shopify
        #     'République dominicaine'  vs 'République Dominique'  (DOP)
        #     'Bahreïn'                 vs 'Bahrëin'               (EUR)
        #     'Koweït'                  vs 'Koweit'                (EUR)
        # C'est la piste du « bug devise DO » poursuivi par Paul depuis le 08/09
        # (bus #5331 puis #5391) : la price list DOP n'est pas corrompue par ce
        # backend, elle n'est simplement JAMAIS écrite par lui. Un produit sans
        # prix fixe dans sa price list se voit servir le prix de base converti
        # par Shopify, ce qui donne exactement le motif « DOP à parité EUR »
        # observé sur Nera puis Soléa, pendant que les 14 produits écrits avant
        # le renommage restent corrects.
        # On NE corrige PAS le nom ici : trancher lequel des deux libellés est
        # canonique rendrait 3 marchés écrivables d'un coup, donc ça change des
        # prix. Décision Théo/Paul. Ici on rend le problème visible.
        unreachable = []
        for name, cfg in COUNTRIES.items():
            if name in live_names:
                continue
            near = [ln for ln in live_names if ln and _fold(ln) == _fold(name)]
            if not near:
                near = [
                    ln for ln in live_names
                    if ln and (_fold(ln) in _fold(name) or _fold(name) in _fold(ln))
                ]
            entry = {
                "market": name,
                "config_currency": cfg.get("currency"),
                "reason": "aucun catalog/price list live à ce nom exact — apply sans effet",
            }
            if near:
                entry["probable_live_name"] = sorted(near)
                entry["reason"] = (
                    "nom désaligné avec Shopify — le marché existe live sous "
                    + " / ".join(f"'{n}'" for n in sorted(near))
                    + ", mais l'écriture cherche le nom exact de countries.py, "
                    "donc tout apply sur ce pays est sans effet (silencieux)."
                )
            unreachable.append(entry)

        # ── unconfigured : marché live SANS config countries.py ──────────────
        # Symétrique du précédent, et jusqu'ici totalement invisible. Ces
        # marchés sont hors de countries=['all'] et donc hors de tout pilotage
        # prix. Mesure du 14/09 : 10 marchés live sans config, dont 'sal'
        # (price list en DOP) et 'Nouvelle' (NZD) — des libellés manifestement
        # tronqués, plus 'Autres', 'Global Market', 'Chypre', 'Egypte',
        # 'Russie'. C'est la réponse à « 5 marchés hors pilotage prix »
        # (bus #5419) : ils ne sont pas mal pilotés, ils sont inconnus du moteur.
        unconfigured = []
        for market in markets:
            name = market.get("name")
            if not name or name in COUNTRIES:
                continue
            price_list = market.get("priceList") or {}
            unconfigured.append({
                "market": name,
                "handle": market.get("handle"),
                "price_list_currency": price_list.get("currency"),
                "enabled": market.get("enabled", True),
                "suggestions": suggest_country_names(name),
                "reason": (
                    "marché live absent de countries.py : exclu de countries=['all'], "
                    "donc jamais écrit par le moteur de prix."
                ),
            })

        return {
            "success": True,
            "summary": {
                "markets_live": len(live_names),
                "configured": len(COUNTRIES),
                "ok": len(ok),
                "blocked": len(blocked),
                "unreachable": len(unreachable),
                "unconfigured": len(unconfigured),
                # Verdict explicite : un lecteur (ou un cron) doit pouvoir
                # tester un booléen sans recompter les listes.
                "all_clear": not blocked and not unreachable and not unconfigured,
            },
            "blocked": blocked,
            "unreachable": unreachable,
            "unconfigured": unconfigured,
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
