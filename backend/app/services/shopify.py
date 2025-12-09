"""
Service Shopify GraphQL pour Luxarmonie
V3 - Fix: matching marchés par nom + pagination produits + récupération tous produits
"""

import httpx
import os
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShopifyService:
    """Service de connexion à Shopify via GraphQL Admin API"""
    
    def __init__(self):
        self.api_version = "2024-10"
    
    @property
    def shop_domain(self) -> str:
        """Lecture dynamique du domain"""
        return os.getenv("SHOPIFY_SHOP_DOMAIN", "")
    
    @property
    def access_token(self) -> str:
        """Lecture dynamique du token"""
        return os.getenv("SHOPIFY_ACCESS_TOKEN", "")
        
    @property
    def graphql_url(self) -> str:
        return f"https://{self.shop_domain}/admin/api/{self.api_version}/graphql.json"
    
    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
    
    async def execute_query(self, query: str, variables: dict = None) -> dict:
        """Exécute une requête GraphQL"""
        logger.info(f"Shopify request to: {self.graphql_url}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            
            try:
                response = await client.post(
                    self.graphql_url,
                    json=payload,
                    headers=self.headers
                )
                logger.info(f"Response status: {response.status_code}")
                
                result = response.json()
                
                if "errors" in result:
                    logger.error(f"GraphQL errors: {result['errors']}")
                
                response.raise_for_status()
                return result
                
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                raise
    
    # ========================================
    # MARKETS
    # ========================================
    
    async def get_all_markets(self) -> List[Dict]:
        """Récupère tous les marchés avec leurs catalogues et priceLists"""
        query = """
        query GetMarkets($first: Int!, $after: String) {
            markets(first: $first, after: $after) {
                edges {
                    node {
                        id
                        name
                        handle
                        enabled
                        primary
                        currencySettings {
                            baseCurrency {
                                currencyCode
                            }
                        }
                        priceList {
                            id
                            name
                            currency
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """
        
        all_markets = []
        has_next = True
        cursor = None
        
        while has_next:
            variables = {"first": 50}
            if cursor:
                variables["after"] = cursor
            
            try:
                result = await self.execute_query(query, variables)
                
                if "data" in result and "markets" in result["data"]:
                    edges = result["data"]["markets"]["edges"]
                    logger.info(f"Found {len(edges)} markets in this batch")
                    
                    for edge in edges:
                        market = edge["node"]
                        market["numericId"] = market["id"].split("/")[-1]
                        all_markets.append(market)
                        cursor = edge["cursor"]
                    
                    has_next = result["data"]["markets"]["pageInfo"]["hasNextPage"]
                else:
                    logger.warning(f"No data in result: {result}")
                    has_next = False
                    
            except Exception as e:
                logger.error(f"Failed to get markets: {str(e)}")
                has_next = False
        
        logger.info(f"Total markets found: {len(all_markets)}")
        return all_markets
    
    # ========================================
    # PRODUCTS - AVEC PAGINATION COMPLÈTE
    # ========================================
    
    async def search_products(self, search: str = "", first: int = 50) -> List[Dict]:
        """Recherche des produits (limité à first)"""
        query = """
        query SearchProducts($first: Int!, $query: String) {
            products(first: $first, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        status
                        featuredImage {
                            url(transform: {maxWidth: 100})
                        }
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    sku
                                    title
                                    price
                                    compareAtPrice
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        try:
            result = await self.execute_query(query, {"first": min(first, 250), "query": search})
            
            if "data" in result and "products" in result["data"]:
                products = []
                for edge in result["data"]["products"]["edges"]:
                    product = edge["node"]
                    product["numericId"] = product["id"].split("/")[-1]
                    product["variants"] = [
                        {
                            **v["node"],
                            "numericId": v["node"]["id"].split("/")[-1]
                        }
                        for v in product["variants"]["edges"]
                    ]
                    products.append(product)
                return products
        except Exception as e:
            logger.error(f"Failed to search products: {str(e)}")
        
        return []
    
    async def get_all_products(self, max_products: int = 2000) -> List[Dict]:
        """
        Récupère TOUS les produits avec pagination
        
        Args:
            max_products: Limite max de produits (défaut 2000)
            
        Returns:
            Liste de tous les produits avec leurs variantes
        """
        query = """
        query GetAllProducts($first: Int!, $after: String) {
            products(first: $first, after: $after) {
                edges {
                    node {
                        id
                        title
                        handle
                        status
                        featuredImage {
                            url(transform: {maxWidth: 100})
                        }
                        variants(first: 100) {
                            edges {
                                node {
                                    id
                                    sku
                                    title
                                    price
                                    compareAtPrice
                                }
                            }
                        }
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
        """
        
        all_products = []
        has_next = True
        cursor = None
        batch_size = 250  # Max Shopify permet
        
        logger.info(f"Starting to fetch all products (max: {max_products})")
        
        while has_next and len(all_products) < max_products:
            variables = {"first": batch_size}
            if cursor:
                variables["after"] = cursor
            
            try:
                result = await self.execute_query(query, variables)
                
                if "data" in result and "products" in result["data"]:
                    edges = result["data"]["products"]["edges"]
                    logger.info(f"Fetched {len(edges)} products (total: {len(all_products) + len(edges)})")
                    
                    for edge in edges:
                        product = edge["node"]
                        product["numericId"] = product["id"].split("/")[-1]
                        product["variants"] = [
                            {
                                **v["node"],
                                "numericId": v["node"]["id"].split("/")[-1]
                            }
                            for v in product["variants"]["edges"]
                        ]
                        all_products.append(product)
                        cursor = edge["cursor"]
                    
                    has_next = result["data"]["products"]["pageInfo"]["hasNextPage"]
                else:
                    has_next = False
                    
            except Exception as e:
                logger.error(f"Failed to get products batch: {str(e)}")
                has_next = False
        
        logger.info(f"Total products fetched: {len(all_products)}")
        return all_products
    
    async def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Récupère un produit par son ID"""
        query = """
        query GetProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                status
                featuredImage {
                    url(transform: {maxWidth: 200})
                }
                variants(first: 100) {
                    edges {
                        node {
                            id
                            sku
                            title
                            price
                            compareAtPrice
                            inventoryQuantity
                        }
                    }
                }
            }
        }
        """
        
        gid = f"gid://shopify/Product/{product_id}" if not product_id.startswith("gid://") else product_id
        
        try:
            result = await self.execute_query(query, {"id": gid})
            
            if "data" in result and result["data"]["product"]:
                product = result["data"]["product"]
                product["numericId"] = product["id"].split("/")[-1]
                product["variants"] = [
                    {
                        **v["node"],
                        "numericId": v["node"]["id"].split("/")[-1]
                    }
                    for v in product["variants"]["edges"]
                ]
                return product
        except Exception as e:
            logger.error(f"Failed to get product: {str(e)}")
        
        return None
    
    # ========================================
    # PRICE LISTS
    # ========================================
    
    async def get_price_list_for_market(self, market_id: str) -> Optional[Dict]:
        """Récupère le PriceList d'un marché"""
        query = """
        query GetMarketPriceList($marketId: ID!) {
            market(id: $marketId) {
                id
                name
                priceList {
                    id
                    name
                    currency
                }
            }
        }
        """
        
        gid = f"gid://shopify/Market/{market_id}" if not market_id.startswith("gid://") else market_id
        
        try:
            result = await self.execute_query(query, {"marketId": gid})
            
            if "data" in result and result["data"]["market"]:
                return result["data"]["market"]["priceList"]
        except Exception as e:
            logger.error(f"Failed to get price list: {str(e)}")
        
        return None
    
    async def get_price_list_prices(
        self, 
        price_list_id: str, 
        variant_ids: List[str] = None,
        first: int = 250
    ) -> List[Dict]:
        """
        Récupère les prix d'une PriceList avec pagination complète
        OPTIMISATION: Si variant_ids fourni, arrête dès qu'on a trouvé tous les prix
        """
        query = """
        query GetPriceListPrices($priceListId: ID!, $first: Int!, $after: String) {
            priceList(id: $priceListId) {
                id
                name
                currency
                prices(first: $first, after: $after) {
                    edges {
                        node {
                            variant {
                                id
                            }
                            price {
                                amount
                                currencyCode
                            }
                            compareAtPrice {
                                amount
                                currencyCode
                            }
                        }
                        cursor
                    }
                    pageInfo {
                        hasNextPage
                    }
                }
            }
        }
        """
        
        gid = f"gid://shopify/PriceList/{price_list_id}" if not price_list_id.startswith("gid://") else price_list_id
        
        all_prices = []
        has_next = True
        cursor = None
        pages_fetched = 0
        max_pages = 100  # Limite de sécurité
        
        # Convertir variant_ids en set pour lookup rapide
        variant_ids_set = None
        if variant_ids:
            # Normaliser les IDs (garder les deux formats)
            variant_ids_set = set()
            for vid in variant_ids:
                variant_ids_set.add(vid)
                # Ajouter aussi l'ID numérique si c'est un GID
                if vid.startswith("gid://"):
                    variant_ids_set.add(vid.split("/")[-1])
                else:
                    # Ajouter le format GID complet
                    variant_ids_set.add(f"gid://shopify/ProductVariant/{vid}")
        
        try:
            while has_next and pages_fetched < max_pages:
                variables = {"priceListId": gid, "first": first}
                if cursor:
                    variables["after"] = cursor
                
                result = await self.execute_query(query, variables)
                pages_fetched += 1
                
                if "data" in result and result["data"]["priceList"]:
                    price_list = result["data"]["priceList"]
                    edges = price_list["prices"]["edges"]
                    
                    if not edges:
                        break
                    
                    for edge in edges:
                        node = edge["node"]
                        variant_id = node["variant"]["id"]
                        variant_numeric = variant_id.split("/")[-1]
                        
                        # Filtrer par variant_ids si fourni
                        if variant_ids_set:
                            if variant_id not in variant_ids_set and variant_numeric not in variant_ids_set:
                                cursor = edge["cursor"]
                                continue
                        
                        price_data = {
                            "variantId": variant_id,
                            "variantNumericId": variant_numeric,
                            "price": node["price"]["amount"],
                            "currency": node["price"]["currencyCode"],
                            "compareAtPrice": node["compareAtPrice"]["amount"] if node.get("compareAtPrice") else None
                        }
                        all_prices.append(price_data)
                        cursor = edge["cursor"]
                    
                    has_next = price_list["prices"]["pageInfo"]["hasNextPage"]
                    
                    # OPTIMISATION: Si on a trouvé tous les variant_ids demandés, on arrête
                    if variant_ids_set and len(all_prices) >= len(variant_ids):
                        logger.info(f"Found all {len(all_prices)} requested prices, stopping pagination")
                        break
                    
                    # Log progress tous les 10 pages
                    if pages_fetched % 10 == 0:
                        logger.info(f"PriceList {gid}: page {pages_fetched}, found {len(all_prices)} prices so far")
                    
                else:
                    has_next = False
                    
        except Exception as e:
            logger.error(f"Failed to get price list prices: {str(e)}")
        
        logger.info(f"PriceList {gid}: completed with {len(all_prices)} prices after {pages_fetched} pages")
        return all_prices
    
    async def get_variant_prices_by_market(
        self,
        variant_ids: List[str],
        market_names: List[str] = None
    ) -> Dict[str, Dict]:
        """
        Récupère les prix de variantes pour plusieurs marchés
        OPTIMISÉ: Parallélisation + limite de pagination stricte
        """
        import asyncio
        
        result = {}
        
        # Récupérer tous les marchés
        markets = await self.get_all_markets()
        logger.info(f"Checking {len(markets)} markets for prices")
        
        # Normaliser les noms de marchés demandés
        market_names_set = set(market_names) if market_names else None
        
        # Filtrer les marchés à traiter
        markets_to_process = []
        for market in markets:
            market_name = market["name"]
            if market_names_set and market_name not in market_names_set:
                continue
            price_list = market.get("priceList")
            if not price_list:
                continue
            markets_to_process.append(market)
        
        logger.info(f"Processing {len(markets_to_process)} markets with PriceLists")
        
        # Fonction pour traiter un marché
        async def process_market(market):
            market_name = market["name"]
            price_list = market["priceList"]
            
            try:
                prices = await self.get_price_list_prices_fast(
                    price_list["id"],
                    variant_ids=variant_ids,
                    max_pages=10  # Limite stricte
                )
                
                market_prices = {}
                for p in prices:
                    market_prices[p["variantId"]] = {
                        "price": p["price"],
                        "compareAtPrice": p["compareAtPrice"],
                        "currency": p["currency"]
                    }
                
                return market_name, {
                    "marketId": market["id"],
                    "currency": price_list["currency"],
                    "priceListId": price_list["id"],
                    "prices": market_prices
                }
            except Exception as e:
                logger.error(f"Error processing market {market_name}: {e}")
                return market_name, None
        
        # Traiter les marchés en parallèle par batches de 5
        batch_size = 5
        for i in range(0, len(markets_to_process), batch_size):
            batch = markets_to_process[i:i + batch_size]
            tasks = [process_market(m) for m in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, Exception):
                    continue
                if res and res[1]:
                    result[res[0]] = res[1]
        
        logger.info(f"Prices fetched for {len(result)} markets")
        return result
    
    async def get_price_list_prices_fast(
        self, 
        price_list_id: str, 
        variant_ids: List[str] = None,
        max_pages: int = 10
    ) -> List[Dict]:
        """
        Version rapide avec limite de pages stricte
        """
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
        pages = 0
        
        # Normaliser variant_ids
        variant_ids_set = set()
        if variant_ids:
            for vid in variant_ids:
                variant_ids_set.add(vid)
                if vid.startswith("gid://"):
                    variant_ids_set.add(vid.split("/")[-1])
                else:
                    variant_ids_set.add(f"gid://shopify/ProductVariant/{vid}")
        
        try:
            while has_next and pages < max_pages:
                variables = {"priceListId": gid, "first": 250}
                if cursor:
                    variables["after"] = cursor
                
                result = await self.execute_query(query, variables)
                pages += 1
                
                if "data" in result and result["data"]["priceList"]:
                    price_list = result["data"]["priceList"]
                    edges = price_list["prices"]["edges"]
                    
                    if not edges:
                        break
                    
                    for edge in edges:
                        node = edge["node"]
                        variant_id = node["variant"]["id"]
                        variant_numeric = variant_id.split("/")[-1]
                        cursor = edge["cursor"]
                        
                        if variant_ids_set:
                            if variant_id not in variant_ids_set and variant_numeric not in variant_ids_set:
                                continue
                        
                        all_prices.append({
                            "variantId": variant_id,
                            "variantNumericId": variant_numeric,
                            "price": node["price"]["amount"],
                            "currency": node["price"]["currencyCode"],
                            "compareAtPrice": node["compareAtPrice"]["amount"] if node.get("compareAtPrice") else None
                        })
                    
                    has_next = price_list["prices"]["pageInfo"]["hasNextPage"]
                    
                    # Arrêt anticipé si tous trouvés
                    if variant_ids_set and len(all_prices) >= len(variant_ids):
                        break
                else:
                    break
                    
        except Exception as e:
            logger.error(f"Error in get_price_list_prices_fast: {e}")
        
        return all_prices
    
    async def update_catalog_prices(
        self, 
        price_list_id: str, 
        price_updates: List[Dict]
    ) -> Dict:
        """
        Met à jour les prix dans un catalogue
        """
        mutation = """
        mutation priceListFixedPricesAdd($priceListId: ID!, $prices: [PriceListPriceInput!]!) {
            priceListFixedPricesAdd(priceListId: $priceListId, prices: $prices) {
                prices {
                    variant {
                        id
                    }
                    price {
                        amount
                        currencyCode
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        prices = []
        for update in price_updates:
            price_input = {
                "variantId": update["variantId"],
                "price": {
                    "amount": str(update["price"]),
                    "currencyCode": update.get("currencyCode", "EUR")
                }
            }
            if update.get("compareAtPrice"):
                price_input["compareAtPrice"] = {
                    "amount": str(update["compareAtPrice"]),
                    "currencyCode": update.get("currencyCode", "EUR")
                }
            prices.append(price_input)
        
        try:
            result = await self.execute_query(mutation, {
                "priceListId": price_list_id,
                "prices": prices
            })
            return result
        except Exception as e:
            logger.error(f"Failed to update prices: {str(e)}")
            return {"error": str(e)}
    
    async def bulk_update_prices(self, market_name: str, updates: List[Dict]) -> Dict:
        """
        Met à jour les prix en bulk pour un marché donné
        
        Args:
            market_name: Nom du marché ("France", "Australie", etc.)
            updates: Liste de {variant_id, price, compare_at_price}
        """
        # Trouver le marché et sa PriceList
        markets = await self.get_all_markets()
        
        target_market = None
        for market in markets:
            if market["name"] == market_name:
                target_market = market
                break
        
        if not target_market:
            return {"success": False, "error": f"Market '{market_name}' not found"}
        
        price_list = target_market.get("priceList")
        if not price_list:
            return {"success": False, "error": f"Market '{market_name}' has no PriceList"}
        
        # Formater les updates
        price_updates = []
        for update in updates:
            price_updates.append({
                "variantId": update["variant_id"],
                "price": update["price"],
                "compareAtPrice": update.get("compare_at_price"),
                "currencyCode": price_list["currency"]
            })
        
        # Appliquer par batches de 100
        batch_size = 100
        results = {"success": True, "updated": 0, "errors": []}
        
        for i in range(0, len(price_updates), batch_size):
            batch = price_updates[i:i + batch_size]
            
            result = await self.update_catalog_prices(price_list["id"], batch)
            
            if "error" in result:
                results["errors"].append(result["error"])
            elif "data" in result:
                user_errors = result["data"].get("priceListFixedPricesAdd", {}).get("userErrors", [])
                if user_errors:
                    for err in user_errors:
                        results["errors"].append(f"{err['field']}: {err['message']}")
                else:
                    results["updated"] += len(batch)
        
        results["success"] = len(results["errors"]) == 0
        return results


# Instance globale
shopify_service = ShopifyService()
