"""
Service de cache des prix - Charge tous les prix au démarrage
Avec persistance JSON pour éviter de recharger à chaque redémarrage
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chemin du fichier cache (utiliser un volume persistant sur Railway)
CACHE_DIR = os.environ.get("CACHE_DIR", "/app/cache")
CACHE_FILE = os.path.join(CACHE_DIR, "price_cache.json")


class PriceCache:
    """
    Cache global des prix par marché avec persistance JSON.
    Structure:
    {
        "France": {
            "currency": "EUR",
            "priceListId": "gid://...",
            "prices": {
                "gid://shopify/ProductVariant/123": {
                    "price": "99.99",
                    "compareAtPrice": "149.99"
                },
                ...
            }
        },
        ...
    }
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._loading = False
        self._loaded = False
        self._last_refresh: Optional[datetime] = None
        self._load_progress = {
            "current_market": "",
            "markets_done": 0,
            "total_markets": 0,
            "total_prices": 0
        }
        
        # Essayer de charger depuis le fichier au démarrage
        self._load_from_file()
    
    def _load_from_file(self) -> bool:
        """Charge le cache depuis le fichier JSON si disponible"""
        try:
            if os.path.exists(CACHE_FILE):
                logger.info(f"Loading cache from file: {CACHE_FILE}")
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._cache = data.get("cache", {})
                self._last_refresh = datetime.fromisoformat(data["last_refresh"]) if data.get("last_refresh") else None
                self._loaded = True
                
                total_prices = sum(len(m.get("prices", {})) for m in self._cache.values())
                logger.info(f"Cache loaded from file: {len(self._cache)} markets, {total_prices} prices")
                logger.info(f"Last refresh: {self._last_refresh}")
                
                return True
        except Exception as e:
            logger.warning(f"Could not load cache from file: {e}")
        
        return False
    
    def _save_to_file(self) -> bool:
        """Sauvegarde le cache dans le fichier JSON"""
        try:
            # Créer le dossier si nécessaire
            os.makedirs(CACHE_DIR, exist_ok=True)
            
            data = {
                "cache": self._cache,
                "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                "saved_at": datetime.now().isoformat()
            }
            
            # Écrire dans un fichier temporaire puis renommer (atomique)
            temp_file = CACHE_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            
            os.replace(temp_file, CACHE_FILE)
            
            file_size = os.path.getsize(CACHE_FILE) / (1024 * 1024)  # MB
            logger.info(f"Cache saved to file: {CACHE_FILE} ({file_size:.1f} MB)")
            
            return True
        except Exception as e:
            logger.error(f"Could not save cache to file: {e}")
            return False
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    @property
    def is_loading(self) -> bool:
        return self._loading
    
    @property
    def last_refresh(self) -> Optional[datetime]:
        return self._last_refresh
    
    @property
    def load_progress(self) -> dict:
        return self._load_progress
    
    def get_status(self) -> dict:
        """Retourne le statut du cache"""
        total_prices = sum(
            len(market_data.get("prices", {})) 
            for market_data in self._cache.values()
        )
        return {
            "loaded": self._loaded,
            "loading": self._loading,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "markets_count": len(self._cache),
            "total_prices": total_prices,
            "progress": self._load_progress,
            "persisted": os.path.exists(CACHE_FILE)
        }
    
    def get_price(self, market_name: str, variant_id: str) -> Optional[dict]:
        """Récupère le prix d'une variante pour un marché"""
        if market_name not in self._cache:
            return None
        
        market_data = self._cache[market_name]
        prices = market_data.get("prices", {})
        
        # Essayer les deux formats d'ID
        if variant_id in prices:
            return prices[variant_id]
        
        # Essayer avec le format GID complet
        if not variant_id.startswith("gid://"):
            gid = f"gid://shopify/ProductVariant/{variant_id}"
            if gid in prices:
                return prices[gid]
        else:
            # Essayer avec juste l'ID numérique
            numeric_id = variant_id.split("/")[-1]
            if numeric_id in prices:
                return prices[numeric_id]
        
        return None
    
    def get_market_data(self, market_name: str) -> Optional[dict]:
        """Récupère toutes les données d'un marché"""
        return self._cache.get(market_name)
    
    def get_prices_for_variants(
        self, 
        variant_ids: List[str], 
        market_names: List[str]
    ) -> Dict[str, Dict]:
        """
        Récupère les prix pour plusieurs variantes et marchés
        Retourne le même format que get_variant_prices_by_market
        """
        result = {}
        
        for market_name in market_names:
            if market_name not in self._cache:
                continue
            
            market_data = self._cache[market_name]
            market_prices = {}
            
            for variant_id in variant_ids:
                price_info = self.get_price(market_name, variant_id)
                if price_info:
                    # Normaliser l'ID
                    if variant_id.startswith("gid://"):
                        key = variant_id
                    else:
                        key = f"gid://shopify/ProductVariant/{variant_id}"
                    market_prices[key] = price_info
            
            if market_prices:
                result[market_name] = {
                    "marketId": market_data.get("marketId", ""),
                    "currency": market_data.get("currency", "EUR"),
                    "priceListId": market_data.get("priceListId", ""),
                    "prices": market_prices
                }
        
        return result
    
    async def load_all_prices(self, shopify_service) -> bool:
        """
        Charge tous les prix de tous les marchés.
        Sauvegarde automatiquement dans le fichier après chargement.
        """
        if self._loading:
            logger.warning("Price cache is already loading")
            return False
        
        self._loading = True
        self._load_progress = {
            "current_market": "Initialisation...",
            "markets_done": 0,
            "total_markets": 0,
            "total_prices": 0
        }
        
        try:
            logger.info("=== STARTING PRICE CACHE LOAD ===")
            
            # Récupérer tous les marchés
            markets = await shopify_service.get_all_markets()
            markets_with_pricelist = [m for m in markets if m.get("priceList")]
            
            self._load_progress["total_markets"] = len(markets_with_pricelist)
            logger.info(f"Found {len(markets_with_pricelist)} markets with PriceLists")
            
            new_cache = {}
            
            for idx, market in enumerate(markets_with_pricelist):
                market_name = market["name"]
                price_list = market["priceList"]
                
                self._load_progress["current_market"] = market_name
                self._load_progress["markets_done"] = idx
                
                logger.info(f"Loading prices for {market_name} ({idx + 1}/{len(markets_with_pricelist)})")
                
                try:
                    # Charger TOUS les prix de ce marché (pas de limite)
                    prices = await self._load_all_pricelist_prices(
                        shopify_service, 
                        price_list["id"]
                    )
                    
                    # Organiser par variant_id
                    prices_dict = {}
                    for p in prices:
                        prices_dict[p["variantId"]] = {
                            "price": p["price"],
                            "compareAtPrice": p["compareAtPrice"],
                            "currency": p["currency"]
                        }
                    
                    new_cache[market_name] = {
                        "marketId": market["id"],
                        "currency": price_list["currency"],
                        "priceListId": price_list["id"],
                        "prices": prices_dict
                    }
                    
                    self._load_progress["total_prices"] += len(prices_dict)
                    logger.info(f"  → {len(prices_dict)} prices loaded for {market_name}")
                    
                except Exception as e:
                    logger.error(f"Error loading prices for {market_name}: {e}")
            
            # Remplacer le cache
            self._cache = new_cache
            self._loaded = True
            self._last_refresh = datetime.now()
            self._load_progress["current_market"] = "Terminé"
            self._load_progress["markets_done"] = len(markets_with_pricelist)
            
            total_prices = sum(len(m.get("prices", {})) for m in self._cache.values())
            logger.info(f"=== PRICE CACHE LOADED: {len(self._cache)} markets, {total_prices} prices ===")
            
            # SAUVEGARDER DANS LE FICHIER
            self._save_to_file()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load price cache: {e}")
            return False
        finally:
            self._loading = False
    
    async def _load_all_pricelist_prices(
        self, 
        shopify_service, 
        price_list_id: str
    ) -> List[dict]:
        """Charge TOUS les prix d'une PriceList (sans limite)"""
        
        query = """
        query GetPriceListPrices($priceListId: ID!, $first: Int!, $after: String) {
            priceList(id: $priceListId) {
                id
                currency
                prices(first: $first, after: $after) {
                    edges {
                        node {
                            variant { id }
                            price { amount currencyCode }
                            compareAtPrice { amount }
                        }
                        cursor
                    }
                    pageInfo { hasNextPage }
                }
            }
        }
        """
        
        gid = f"gid://shopify/PriceList/{price_list_id}" if not price_list_id.startswith("gid://") else price_list_id
        
        all_prices = []
        has_next = True
        cursor = None
        
        while has_next:
            variables = {"priceListId": gid, "first": 250}
            if cursor:
                variables["after"] = cursor
            
            try:
                result = await shopify_service.execute_query(query, variables)
                
                if "data" in result and result["data"]["priceList"]:
                    price_list = result["data"]["priceList"]
                    edges = price_list["prices"]["edges"]
                    
                    if not edges:
                        break
                    
                    for edge in edges:
                        node = edge["node"]
                        all_prices.append({
                            "variantId": node["variant"]["id"],
                            "price": node["price"]["amount"],
                            "currency": node["price"]["currencyCode"],
                            "compareAtPrice": node["compareAtPrice"]["amount"] if node.get("compareAtPrice") else None
                        })
                        cursor = edge["cursor"]
                    
                    has_next = price_list["prices"]["pageInfo"]["hasNextPage"]
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching prices: {e}")
                break
        
        return all_prices


    def update_prices(self, updates: List[dict], save: bool = True) -> int:
        """
        Met à jour les prix dans le cache après un Apply.
        
        Args:
            updates: Liste de {"market": str, "variant_id": str, "price": str, "compare_at_price": str}
            save: Sauvegarder dans le fichier après mise à jour
            
        Returns:
            Nombre de prix mis à jour
        """
        updated_count = 0
        
        for update in updates:
            market_name = update.get("market")
            variant_id = update.get("variant_id")
            new_price = update.get("price")
            compare_at = update.get("compare_at_price")
            
            if not market_name or not variant_id:
                continue
            
            if market_name not in self._cache:
                logger.warning(f"Market {market_name} not in cache, skipping update")
                continue
            
            # Normaliser l'ID variant
            if not variant_id.startswith("gid://"):
                gid = f"gid://shopify/ProductVariant/{variant_id}"
            else:
                gid = variant_id
            
            # Mettre à jour le prix
            if "prices" not in self._cache[market_name]:
                self._cache[market_name]["prices"] = {}
            
            self._cache[market_name]["prices"][gid] = {
                "price": str(new_price),
                "compareAtPrice": str(compare_at) if compare_at else None,
                "currency": self._cache[market_name].get("currency", "EUR")
            }
            updated_count += 1
        
        if updated_count > 0:
            logger.info(f"Cache updated with {updated_count} new prices")
            self._last_refresh = datetime.now()
            
            if save:
                self._save_to_file()
        
        return updated_count
    
    def get_all_markets(self) -> List[str]:
        """Retourne la liste de tous les marchés dans le cache"""
        return list(self._cache.keys())


# Instance globale du cache
price_cache = PriceCache()
