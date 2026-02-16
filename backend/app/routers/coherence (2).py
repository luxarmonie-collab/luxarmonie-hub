"""
Module d'analyse de cohérence des prix V2
- Niveau 1: Cohérence intra-produit (tailles croissantes)
- Niveau 2: Cohérence cross-marchés (écarts vs France)
- Niveau 3: Résumé IA via Claude API
"""

import re
import os
import math
import logging
import httpx
from typing import List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.shopify import shopify_service
from app.services.price_cache import price_cache
from app.config.countries import COUNTRIES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/coherence", tags=["coherence"])


# ========================================
# MODELS
# ========================================

class AnalyzeRequest(BaseModel):
    tolerance_percent: float = 15.0
    reference_market: str = "France"
    target_market: Optional[str] = None  # None = tous les marchés
    analysis_types: List[str] = ["intra_product", "cross_market"]


class ApplyCorrectionsRequest(BaseModel):
    corrections: List[dict]
    dry_run: bool = False


# ========================================
# HELPERS - PARSING TAILLES
# ========================================

def extract_size_value(variant_title: str) -> Optional[float]:
    """
    Extrait une valeur numérique de taille depuis le titre de variante.
    Gère: 'Diamètre 50cm', '40 cm', '100cm', 'S', 'M', 'L', 'XL', etc.
    """
    if not variant_title:
        return None

    title = variant_title.strip().lower()

    # Pattern 1: Nombre + cm/mm/m (ex: "Diamètre 50cm", "40 cm", "100cm")
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cm|mm|m\b)', title)
    if match:
        val = float(match.group(1))
        # Convertir mm en cm pour comparaison
        if 'mm' in title:
            val = val / 10
        return val

    # Pattern 2: Nombre seul significatif (ex: "30", "50")
    match = re.search(r'\b(\d+(?:\.\d+)?)\b', title)
    if match:
        val = float(match.group(1))
        if val >= 5 and val <= 500:  # Plausible comme dimension
            return val

    # Pattern 3: Tailles S/M/L/XL
    size_map = {
        'xxs': 1, 'xs': 2, 's': 3, 'small': 3,
        'm': 4, 'medium': 4,
        'l': 5, 'large': 5,
        'xl': 6, 'xxl': 7, 'xxxl': 8,
        '2xl': 7, '3xl': 8
    }
    for size_name, size_val in size_map.items():
        if re.search(r'\b' + re.escape(size_name) + r'\b', title):
            return size_val

    return None


def get_size_from_variant(variant_title: str) -> Tuple[Optional[float], str]:
    """Retourne (valeur_taille, type_taille) pour grouper les variantes comparables"""
    if not variant_title:
        return None, "unknown"

    title = variant_title.lower()
    size_val = extract_size_value(variant_title)

    if size_val is None:
        return None, "unknown"

    if re.search(r'cm|mm|m\b|diamètre|diametre|longueur|largeur|hauteur', title):
        return size_val, "dimension"
    elif re.search(r'\b(xxs|xs|s|m|l|xl|xxl|xxxl|2xl|3xl|small|medium|large)\b', title):
        return size_val, "letter"
    else:
        return size_val, "numeric"


# ========================================
# ANALYSE NIVEAU 1 - INTRA-PRODUIT
# ========================================

async def analyze_intra_product(products_map: Dict, market_name: str, market_prices: Dict) -> List[dict]:
    """
    Détecte les incohérences de prix au sein d'un même produit.
    Ex: 40cm à 150€ et 100cm à 120€ → CRITIQUE
    """
    anomalies = []
    market_currency = market_prices.get("currency", "EUR") if isinstance(market_prices, dict) else "EUR"
    prices_dict = market_prices.get("prices", {}) if isinstance(market_prices, dict) else {}

    for product_id, product_info in products_map.items():
        product_title = product_info.get("title", "Unknown")
        variants = product_info.get("variants", [])

        if len(variants) < 2:
            continue

        # Grouper les variantes par couleur/type (pour ne comparer que les tailles)
        # Extraire la partie "couleur" et la partie "taille"
        size_groups = {}  # color_key -> [(size_val, variant_id, price, variant_title)]

        for variant in variants:
            variant_id = variant.get("id", "")
            variant_title = variant.get("title", "")

            # Récupérer le prix du marché
            price_info = prices_dict.get(variant_id)
            if not price_info:
                # Essayer avec le format numérique
                numeric_id = variant_id.split("/")[-1] if "/" in variant_id else variant_id
                price_info = prices_dict.get(f"gid://shopify/ProductVariant/{numeric_id}")
                if not price_info:
                    price_info = prices_dict.get(numeric_id)
            if not price_info:
                continue

            price = float(price_info.get("price", 0))
            if price <= 0:
                continue

            size_val, size_type = get_size_from_variant(variant_title)
            if size_val is None:
                continue

            # Extraire la "couleur" (tout sauf la taille) pour grouper
            color_key = re.sub(r'\d+\s*(?:cm|mm|m)\b', '', variant_title, flags=re.IGNORECASE).strip()
            color_key = re.sub(r'diamètre|diametre|longueur|largeur|hauteur', '', color_key, flags=re.IGNORECASE).strip()
            color_key = re.sub(r'\s+', ' ', color_key).strip(' -/')
            if not color_key:
                color_key = "default"

            group_key = f"{size_type}:{color_key.lower()}"

            if group_key not in size_groups:
                size_groups[group_key] = []
            size_groups[group_key].append((size_val, variant_id, price, variant_title))

        # Analyser chaque groupe de tailles
        for group_key, items in size_groups.items():
            if len(items) < 2:
                continue

            # Trier par taille
            items.sort(key=lambda x: x[0])

            # Vérifier que le prix est croissant (ou au moins pas décroissant)
            for i in range(1, len(items)):
                prev_size, prev_vid, prev_price, prev_title = items[i - 1]
                curr_size, curr_vid, curr_price, curr_title = items[i]

                # Si la taille est plus grande mais le prix est PLUS BAS → anomalie
                if curr_size > prev_size and curr_price < prev_price:
                    price_diff_pct = abs((curr_price - prev_price) / prev_price) * 100

                    # Déterminer la sévérité
                    if price_diff_pct > 20:
                        severity = "critical"
                    elif price_diff_pct > 10:
                        severity = "warning"
                    else:
                        severity = "minor"

                    anomalies.append({
                        "type": "intra_product",
                        "severity": severity,
                        "product_title": product_title,
                        "product_id": product_id,
                        "variant_id": curr_vid,
                        "variant_title": curr_title,
                        "market": market_name,
                        "currency": market_currency,
                        "current_price": curr_price,
                        "reference_variant_title": prev_title,
                        "reference_price": prev_price,
                        "deviation_percent": round(price_diff_pct, 1),
                        "suggested_price": round(prev_price * (curr_size / prev_size), 2),
                        "description": f"'{curr_title}' ({curr_price} {market_currency}) est moins cher que '{prev_title}' ({prev_price} {market_currency}) alors que la taille est plus grande"
                    })

    return anomalies


# ========================================
# ANALYSE NIVEAU 2 - CROSS-MARCHÉS
# ========================================

async def analyze_cross_market(
    products_map: Dict,
    reference_market: str,
    ref_cache: Dict,
    target_markets: List[str],
    tolerance_percent: float
) -> List[dict]:
    """
    Compare les prix entre le marché de référence et les autres marchés.
    Tient compte des taux de change configurés.
    """
    anomalies = []

    ref_prices = ref_cache.get("prices", {})
    ref_currency = ref_cache.get("currency", "EUR")

    for market_name in target_markets:
        if market_name == reference_market:
            continue

        market_data = price_cache._cache.get(market_name)
        if not market_data:
            continue

        market_prices = market_data.get("prices", {})
        market_currency = market_data.get("currency", "EUR")
        market_config = COUNTRIES.get(market_name, {})
        expected_rate = market_config.get("exchange_rate", 1.0)

        if expected_rate <= 0:
            expected_rate = 1.0

        for variant_id, ref_price_info in ref_prices.items():
            if variant_id not in market_prices:
                continue

            ref_price = float(ref_price_info.get("price", 0))
            market_price = float(market_prices[variant_id].get("price", 0))

            if ref_price <= 0 or market_price <= 0:
                continue

            expected_price = ref_price * expected_rate

            if expected_price > 0:
                deviation_percent = abs((market_price - expected_price) / expected_price) * 100
            else:
                continue

            if deviation_percent > tolerance_percent:
                if deviation_percent > 50:
                    severity = "critical"
                elif deviation_percent > 30:
                    severity = "warning"
                else:
                    severity = "minor"

                # Trouver le nom du produit
                product_title = "Produit inconnu"
                variant_title = ""
                for pid, pinfo in products_map.items():
                    for v in pinfo.get("variants", []):
                        if v.get("id") == variant_id:
                            product_title = pinfo.get("title", "")
                            variant_title = v.get("title", "")
                            break

                anomalies.append({
                    "type": "cross_market",
                    "severity": severity,
                    "product_title": product_title,
                    "variant_id": variant_id,
                    "variant_title": variant_title,
                    "market": market_name,
                    "currency": market_currency,
                    "current_price": market_price,
                    "reference_market": reference_market,
                    "reference_price": ref_price,
                    "reference_currency": ref_currency,
                    "expected_price": round(expected_price, 2),
                    "exchange_rate": expected_rate,
                    "deviation_percent": round(deviation_percent, 1),
                    "suggested_price": round(expected_price, 2),
                    "description": f"Écart de {round(deviation_percent, 1)}% vs {reference_market} (attendu ~{round(expected_price, 2)} {market_currency}, actuel {market_price} {market_currency})"
                })

    return anomalies


# ========================================
# NIVEAU 3 - RÉSUMÉ IA CLAUDE
# ========================================

async def generate_ai_summary(anomalies: List[dict], stats: dict, reference_market: str) -> Optional[str]:
    """Génère un résumé intelligent via Claude API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping AI summary")
        return None

    # Préparer un résumé des anomalies pour Claude
    intra_anomalies = [a for a in anomalies if a["type"] == "intra_product"]
    cross_anomalies = [a for a in anomalies if a["type"] == "cross_market"]

    # Grouper par marché pour les cross-market
    market_summary = {}
    for a in cross_anomalies:
        m = a["market"]
        if m not in market_summary:
            market_summary[m] = {"count": 0, "critical": 0, "avg_deviation": 0, "deviations": []}
        market_summary[m]["count"] += 1
        if a["severity"] == "critical":
            market_summary[m]["critical"] += 1
        market_summary[m]["deviations"].append(a["deviation_percent"])

    for m in market_summary:
        devs = market_summary[m]["deviations"]
        market_summary[m]["avg_deviation"] = round(sum(devs) / len(devs), 1) if devs else 0
        del market_summary[m]["deviations"]

    # Top 10 anomalies critiques pour le contexte
    top_critical = sorted(anomalies, key=lambda x: -x["deviation_percent"])[:10]
    top_examples = []
    for a in top_critical:
        top_examples.append({
            "product": a.get("product_title", ""),
            "variant": a.get("variant_title", ""),
            "market": a.get("market", ""),
            "type": a["type"],
            "deviation": f"{a['deviation_percent']}%",
            "current_price": f"{a['current_price']} {a.get('currency', '')}",
            "description": a.get("description", "")
        })

    prompt = f"""Tu es l'assistant pricing de Luxarmonie, une marque premium de luminaires design.
Analyse ce rapport de cohérence des prix et donne un résumé actionnable en français.

STATS GLOBALES:
- Marché de référence: {reference_market}
- Anomalies intra-produit (taille incohérente): {len(intra_anomalies)}
- Anomalies cross-marchés: {len(cross_anomalies)}
- Total: {stats.get('total_anomalies', 0)}
- Critiques: {stats.get('by_severity', {}).get('critical', 0)}
- Alertes: {stats.get('by_severity', {}).get('warning', 0)}
- Mineures: {stats.get('by_severity', {}).get('minor', 0)}

RÉSUMÉ PAR MARCHÉ (top problèmes):
{str(dict(sorted(market_summary.items(), key=lambda x: -x[1]['count'])[:10]))}

TOP 10 ANOMALIES CRITIQUES:
{str(top_examples)}

Donne:
1. Un résumé exécutif (2-3 phrases)
2. Les marchés les plus problématiques à corriger en priorité
3. Les types de problèmes récurrents
4. Des recommandations concrètes

Sois concis, direct et utilise des emojis pour la lisibilité. Réponds en français."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"]
            else:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        return None


# ========================================
# ENDPOINTS
# ========================================

@router.get("/markets")
async def get_coherence_markets():
    """Retourne les marchés disponibles pour l'analyse"""
    if not price_cache.is_loaded:
        return {"markets": list(COUNTRIES.keys()), "source": "static"}

    markets = []
    for market_name, market_data in price_cache._cache.items():
        markets.append({
            "name": market_name,
            "currency": market_data.get("currency", "EUR"),
            "prices_count": len(market_data.get("prices", {})),
            "has_config": market_name in COUNTRIES
        })

    markets.sort(key=lambda x: x["name"])
    return {"markets": markets, "source": "cache"}


@router.post("/analyze")
async def analyze_coherence(request: AnalyzeRequest):
    """
    Analyse complète de cohérence des prix.
    Retourne les anomalies intra-produit et cross-marchés avec noms de produits.
    """
    if not price_cache.is_loaded or len(price_cache._cache) == 0:
        raise HTTPException(status_code=400, detail="Le cache des prix n'est pas chargé.")

    reference_market = request.reference_market
    if reference_market not in price_cache._cache:
        raise HTTPException(status_code=400, detail=f"Le marché '{reference_market}' n'existe pas dans le cache.")

    ref_cache = price_cache._cache[reference_market]

    logger.info(f"Starting coherence analysis V2 - ref: {reference_market}, types: {request.analysis_types}")

    # ========================================
    # CHARGER LES NOMS DE PRODUITS
    # ========================================
    logger.info("Loading product names from Shopify...")
    products_map = {}  # product_id -> {title, variants: [{id, title, sku, price}]}

    try:
        all_products = await shopify_service.get_all_products(max_products=2000)
        for product in all_products:
            pid = product.get("id", "")
            products_map[pid] = {
                "title": product.get("title", ""),
                "handle": product.get("handle", ""),
                "variants": [
                    {
                        "id": v.get("id", ""),
                        "title": v.get("title", ""),
                        "sku": v.get("sku", ""),
                        "price": v.get("price", "0")
                    }
                    for v in product.get("variants", [])
                ]
            }
        logger.info(f"Loaded {len(products_map)} products")
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        # Continue sans les noms, c'est pas bloquant

    # ========================================
    # DÉTERMINER LES MARCHÉS CIBLES
    # ========================================
    if request.target_market:
        target_markets = [request.target_market]
    else:
        target_markets = [m for m in price_cache._cache.keys() if m != reference_market]

    # ========================================
    # LANCER LES ANALYSES
    # ========================================
    all_anomalies = []

    # Niveau 1: Intra-produit
    if "intra_product" in request.analysis_types:
        logger.info("Running intra-product analysis...")

        # Analyser le marché de référence
        intra_ref = await analyze_intra_product(products_map, reference_market, ref_cache)
        all_anomalies.extend(intra_ref)

        # Analyser chaque marché cible
        for market_name in target_markets:
            market_data = price_cache._cache.get(market_name)
            if market_data and market_data.get("prices"):
                intra_market = await analyze_intra_product(products_map, market_name, market_data)
                all_anomalies.extend(intra_market)

        logger.info(f"Intra-product: {len([a for a in all_anomalies if a['type'] == 'intra_product'])} anomalies")

    # Niveau 2: Cross-marchés
    if "cross_market" in request.analysis_types:
        logger.info("Running cross-market analysis...")
        cross = await analyze_cross_market(
            products_map, reference_market, ref_cache,
            target_markets, request.tolerance_percent
        )
        all_anomalies.extend(cross)
        logger.info(f"Cross-market: {len(cross)} anomalies")

    # ========================================
    # STATS
    # ========================================
    stats = {
        "total_anomalies": len(all_anomalies),
        "total_variants_analyzed": len(ref_cache.get("prices", {})),
        "markets_analyzed": target_markets,
        "by_type": {
            "intra_product": len([a for a in all_anomalies if a["type"] == "intra_product"]),
            "cross_market": len([a for a in all_anomalies if a["type"] == "cross_market"]),
        },
        "by_severity": {
            "critical": len([a for a in all_anomalies if a["severity"] == "critical"]),
            "warning": len([a for a in all_anomalies if a["severity"] == "warning"]),
            "minor": len([a for a in all_anomalies if a["severity"] == "minor"]),
        }
    }

    # Trier: critiques en premier, puis par écart décroissant
    severity_order = {"critical": 3, "warning": 2, "minor": 1}
    all_anomalies.sort(key=lambda x: (-severity_order.get(x["severity"], 0), -x["deviation_percent"]))

    # ========================================
    # RÉSUMÉ IA (Niveau 3)
    # ========================================
    ai_summary = None
    if len(all_anomalies) > 0:
        ai_summary = await generate_ai_summary(all_anomalies, stats, reference_market)

    logger.info(f"Coherence analysis complete: {stats['total_anomalies']} anomalies")

    return {
        "stats": stats,
        "anomalies": all_anomalies[:500],
        "ai_summary": ai_summary,
        "reference_market": reference_market,
        "tolerance_percent": request.tolerance_percent
    }


@router.post("/apply")
async def apply_corrections(request: ApplyCorrectionsRequest):
    """Applique les corrections de cohérence sur Shopify"""
    from app.routers.pricing import apply_psychological_ending, calculate_compare_at

    if request.dry_run:
        return {
            "applied": False,
            "dry_run": True,
            "would_update": len(request.corrections)
        }

    # Grouper par marché
    corrections_by_market = {}
    for correction in request.corrections:
        market = correction.get("market")
        if market not in corrections_by_market:
            corrections_by_market[market] = []

        suggested_price = float(correction.get("suggested_price", 0))
        final_price = apply_psychological_ending(suggested_price, market)
        compare_at_raw = calculate_compare_at(final_price, 0.40)
        compare_at_price = apply_psychological_ending(compare_at_raw, market)

        corrections_by_market[market].append({
            "variant_id": correction.get("variant_id"),
            "price": final_price,
            "compare_at_price": compare_at_price
        })

    results = {"success": [], "errors": [], "updated_count": 0}
    cache_updates = []

    for market, corrections in corrections_by_market.items():
        try:
            update_result = await shopify_service.bulk_update_prices(market, corrections)
            if update_result.get("success"):
                updated = update_result.get("updated", len(corrections))
                results["success"].append({"market": market, "updated": updated})
                results["updated_count"] += updated
                for corr in corrections:
                    cache_updates.append({
                        "market": market,
                        "variant_id": corr["variant_id"],
                        "price": corr["price"],
                        "compare_at_price": corr["compare_at_price"]
                    })
            else:
                results["errors"].append(f"{market}: {update_result.get('error')}")
        except Exception as e:
            results["errors"].append(f"{market}: {str(e)}")

    if cache_updates:
        price_cache.update_prices(cache_updates, save=True)

    return {"applied": True, "results": results}
