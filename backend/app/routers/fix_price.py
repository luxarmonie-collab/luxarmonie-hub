"""
Router pour la correction de prix individuels
- Mode "Prix fixe" : définir un prix EUR et recalculer tous les marchés
- Mode "Copier variante" : copier les prix d'une variante modèle vers d'autres
"""

from fastapi import APIRouter, HTTPException
from app.services.shopify import shopify_service
from app.services.price_cache import price_cache
from app.config.countries import (
    COUNTRIES,
    NO_DECIMAL_CURRENCIES,
    UnknownCountryError,
    apply_ending,
    get_currency_strict,
    get_exchange_rate_strict,
    is_known_country,
    resolve_country,
    suggest_country_names,
)
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


# ════════════════════════════════════════════════════════════════════════════
# CALCUL — délégué à app/config/countries.py (source unique)
#
# Leo 2026-09-14. Ce fichier portait sa PROPRE table COUNTRY_ROUNDING de 52
# entrées, dérivée du champ `ending` de countries.py. Écarts mesurés sur les
# 62 pays configurés avant suppression :
#   - 10 pays absents de la table -> arrondis en .99 par défaut, dont Japon
#     (JPY) et Corée du Sud (KRW) qui doivent finir en 000. C'est la source du
#     « JP 22 937,99 JPY » remonté par Paul (bus #5391) : des centimes sur une
#     devise qui n'en a pas. Également Koweït/Oman/Jordanie/Liban/Pakistan
#     (attendus en 00), Bulgarie/Roumanie/République dominicaine.
#   - Afrique du Sud en 00 ici, 9_int dans countries.py.
#   - clé morte 'Hong Kong' (le marché Shopify s'appelle 'Honk Hong').
# Une table dupliquée finit toujours par dériver de son original. Il n'y en a
# plus qu'une : COUNTRIES[pays]["ending"].
# ════════════════════════════════════════════════════════════════════════════


def get_exchange_rate(country: str) -> float:
    """Taux de change. Lève UnknownCountryError sur pays inconnu (plus de 1.0)."""
    return get_exchange_rate_strict(country)


def get_currency(country: str) -> str:
    """Devise déclarée. Lève UnknownCountryError sur pays inconnu (plus de 'EUR')."""
    return get_currency_strict(country)


def calculate_price_for_country(base_price_eur: float, country: str) -> float:
    """
    Prix pour un pays à partir d'un prix EUR de référence.
    Applique : taux de change + terminaison psychologique du pays.

    ⚠️ LIMITE CONNUE, NON CORRIGÉE ICI — décision business en attente.
    Le champ `adjustment` de countries.py ('vat' -> -12% puis +TVA locale,
    'minus_10' -> -10%) n'est PAS appliqué : on multiplie la base par le taux
    BRUT. Conséquence mesurée par Paul (bus #5364, 11/09) : le ratio
    preview/base vaut exactement l'exchange_rate (UK 0.88) alors que le ratio
    réel du store est 0.757 — un apply piloté par ce moteur remonterait
    UK/US/JP/KR/CH d'environ +16 %.
    Le correctif technique est prêt et documenté depuis le 15/06 dans
    agents/LuminairePricing/BRIEF-TVA-fix-price-2026-06-15.md : câbler
    services/pricing_engine.py::calculate_price() ici. Il n'est PAS appliqué
    parce qu'il reprix TOUT le catalogue et que la config elle-même est en
    question (France vat=0.19 ou 0.20 ? USA exchange_rate=1.20 = markup ou
    bug ?). Ça se tranche avec Théo, pas dans un commit.
    En attendant, /preview le DIT (champ `warnings`) au lieu de laisser croire
    que le calcul est complet.
    """
    exchange_rate = get_exchange_rate_strict(country)
    converted = base_price_eur * exchange_rate
    return apply_ending(converted, country)


def format_price(price: float, country: str) -> str:
    """Formate le prix selon la devise du pays."""
    currency = get_currency_strict(country)
    if currency in NO_DECIMAL_CURRENCIES:
        return str(int(price))
    return f"{price:.2f}"


def _resolve_requested_countries(requested: List[str]) -> tuple:
    """
    Transforme la liste de pays demandée en (pays_canoniques, warnings).

    Deux régimes, volontairement différents :

    - Pays nommés EXPLICITEMENT par l'appelant : un nom inconnu est une FAUTE,
      on lève (400). Demande de Paul (bus #5338) : « rejeter en 400 tout nom de
      pays absent de countries.py plutôt que de faire un fallback ». Une faute
      de frappe ne doit pas produire un preview d'apparence valide visant une
      autre price list.

    - Expansion de 'all' : les noms viennent du cache Shopify, pas de
      l'appelant. Lever ferait tomber le récap quotidien de Paul à la première
      création de marché. On IGNORE donc les marchés non configurés, mais on
      les NOMME dans les warnings : un skip anonyme cache un incident (65 pros
      bloqués 4 semaines derrière un `skipped` fourre-tout, août 2026).
    """
    warnings: List[str] = []
    if 'all' in requested:
        live_markets = price_cache.get_all_markets()
        if not live_markets:
            warnings.append(
                "Cache prix vide : 'all' est retombé sur les 62 pays de countries.py. "
                "Les prix actuels affichés seront tous vides. Lancer POST /api/cache/refresh."
            )
            return list(COUNTRIES.keys()), warnings
        known = [m for m in live_markets if is_known_country(m)]
        unknown = [m for m in live_markets if not is_known_country(m)]
        if unknown:
            warnings.append(
                f"{len(unknown)} marché(s) Shopify live IGNORÉ(S) par 'all' faute de config "
                f"dans countries.py — aucun prix ne leur sera proposé : "
                + ", ".join(f"'{u}'" for u in sorted(unknown))
                + ". Voir GET /api/markets/currency-check (section unconfigured)."
            )
        missing = [c for c in COUNTRIES if not any(is_known_country(m) and resolve_country(m) == c for m in live_markets)]
        if missing:
            warnings.append(
                f"{len(missing)} pays configuré(s) ABSENT(S) du cache prix, donc hors de 'all' "
                f"(cache incomplet ou marché non créé côté Shopify) : "
                + ", ".join(f"'{m}'" for m in sorted(missing))
                + ". Voir GET /api/cache/status."
            )
        return [resolve_country(m) for m in known], warnings

    unknown = [c for c in requested if not is_known_country(c)]
    if unknown:
        detail = {
            "error": "unknown_country",
            "message": (
                "Nom(s) de pays absent(s) de countries.py. Refus explicite : un nom "
                "inconnu produisait avant un preview en EUR au taux 1.0, qui appliqué "
                "aurait écrit le prix de base brut dans une price list partagée."
            ),
            "unknown_countries": unknown,
            "suggestions": {c: suggest_country_names(c) for c in unknown},
            "valid_countries": sorted(COUNTRIES.keys()),
        }
        raise HTTPException(status_code=400, detail=detail)
    return [resolve_country(c) for c in requested], warnings


def _engine_warnings(countries: List[str]) -> List[str]:
    """
    Réserves à joindre à TOUT preview. Objectif : que le lecteur du preview
    n'ait pas à re-diagnostiquer le moteur à chaque fois (Paul l'a refait le
    11/09 puis le 12/09 puis le 13/09).
    """
    out: List[str] = []
    out.append(
        "MOTEUR INCOMPLET — `adjustment` ('vat' / 'minus_10') non appliqué : "
        "new_price = base_eur x exchange_rate brut x terminaison. Les prix live du "
        "store intègrent l'adjustment, donc un apply piloté par ce preview DÉCALE "
        "les prix (≈ +16 % sur UK/US/JP/KR/CH). Décision Théo en attente depuis le "
        "2026-06-15 (BRIEF-TVA-fix-price-2026-06-15.md). Ne pas appliquer en masse."
    )
    cache_status = price_cache.get_status()
    if cache_status.get("stale_hours") is not None and cache_status["stale_hours"] > 26:
        out.append(
            f"Cache prix daté de {cache_status['stale_hours']}h "
            f"(dernier refresh {cache_status.get('last_refresh')}) : les `current_price` "
            f"affichés peuvent être périmés. Lancer POST /api/cache/refresh."
        )
    if cache_status.get("complete") is False:
        out.append(
            f"Cache prix INCOMPLET — {cache_status.get('markets_cached')} marché(s) en cache "
            f"pour {cache_status.get('markets_expected')} attendus "
            f"(dernier marché traité : {cache_status.get('last_market_seen')}). "
            f"Les marchés manquants sortent en current_price=null, ce qui ressemble à "
            f"« jamais pricé » alors que le live a des prix."
        )
    return out


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
        # Résolution STRICTE des marchés demandés (plus de fallback EUR muet).
        # HTTPException(400) remonte telle quelle : voir le `except HTTPException`
        # plus bas — sans lui, le `except Exception` la retransformait en 500 et
        # l'appelant perdait la liste des noms valides.
        countries, country_warnings = _resolve_requested_countries(request.countries)
        if not countries:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_target_market",
                    "message": (
                        "Aucun marché exploitable après résolution. Le cache prix est "
                        "probablement vide ou ne contient que des marchés non configurés."
                    ),
                },
            )

        warnings = _engine_warnings(countries) + country_warnings
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
                    "price_diff_percent": price_diff,
                    # Calcul exposé ligne à ligne : Paul a dû mesurer le ratio
                    # new/base à la main pour découvrir que l'adjustment sautait.
                    # Le preview doit montrer son propre calcul.
                    "exchange_rate": COUNTRIES[country]["exchange_rate"],
                    "ending": COUNTRIES[country]["ending"],
                    "adjustment_declared": COUNTRIES[country]["adjustment"],
                    "adjustment_applied": False,
                })
        
        return {
            "success": True,
            "summary": {
                "variants_count": len(request.variant_ids),
                "countries_count": len(countries),
                "total_updates": len(preview_items),
                "base_price_eur": request.base_price_eur,
                "compare_at_price_eur": request.compare_at_price_eur,
                # adjustment_applied=False est explicite et non négociable tant que
                # le brief TVA n'est pas tranché. Un lecteur (humain ou script) doit
                # pouvoir tester ce booléen au lieu de lire une note de bas de page.
                "adjustment_applied": False,
                "warnings_count": len(warnings),
            },
            "warnings": warnings,
            "preview": preview_items
        }

    except HTTPException:
        raise
    except UnknownCountryError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "unknown_country", "message": str(e),
                    "suggestions": e.suggestions},
        )
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
