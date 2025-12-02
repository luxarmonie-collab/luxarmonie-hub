"""
Service Shopify GraphQL pour Luxarmonie
Gère toutes les interactions avec l'API Shopify
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
        logger.info(f"Token preview: {self.access_token[:15]}..." if self.access_token else "NO TOKEN!")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                
                # Log errors if any
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
                        # Extraire l'ID numérique du GID
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
    # PRODUCTS
    # ========================================
    
    async def search_products(self, search: str = "", first: int = 50) -> List[Dict]:
        """Recherche des produits"""
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
            result = await self.execute_query(query, {"first": first, "query": search})
            
            if "data" in result and "products" in result["data"]:
                products = []
                for edge in result["data"]["products"]["edges"]:
                    product = edge["node"]
                    product["numericId"] = product["id"].split("/")[-1]
                    # Flatten variants
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
                product["variants"] = [v["node"] for v in product["variants"]["edges"]]
                return product
        except Exception as e:
            logger.error(f"Failed to get product: {str(e)}")
        
        return None
    
    # ========================================
    # CATALOG PRICING
    # ========================================
    
    async def get_catalog_price_list(self, market_id: str) -> Optional[Dict]:
        """Récupère la price list d'un marché"""
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
        first: int = 100
    ) -> List[Dict]:
        """
        Récupère les prix d'une PriceList pour des variantes données
        
        Args:
            price_list_id: ID de la PriceList (gid://shopify/PriceList/xxx)
            variant_ids: Liste optionnelle d'IDs de variantes à filtrer
            first: Nombre max de prix à retourner
            
        Returns:
            Liste de {variantId, price, compareAtPrice, currency}
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
        
        try:
            while has_next:
                variables = {"priceListId": gid, "first": first}
                if cursor:
                    variables["after"] = cursor
                
                result = await self.execute_query(query, variables)
                
                if "data" in result and result["data"]["priceList"]:
                    price_list = result["data"]["priceList"]
                    edges = price_list["prices"]["edges"]
                    
                    for edge in edges:
                        node = edge["node"]
                        price_data = {
                            "variantId": node["variant"]["id"],
                            "variantNumericId": node["variant"]["id"].split("/")[-1],
                            "price": node["price"]["amount"],
                            "currency": node["price"]["currencyCode"],
                            "compareAtPrice": node["compareAtPrice"]["amount"] if node.get("compareAtPrice") else None
                        }
                        
                        # Filtrer par variant_ids si fourni
                        if variant_ids is None or price_data["variantId"] in variant_ids or price_data["variantNumericId"] in variant_ids:
                            all_prices.append(price_data)
                        
                        cursor = edge["cursor"]
                    
                    has_next = price_list["prices"]["pageInfo"]["hasNextPage"]
                    
                    # Limiter pour éviter trop de requêtes
                    if len(all_prices) >= 500:
                        has_next = False
                else:
                    has_next = False
                    
        except Exception as e:
            logger.error(f"Failed to get price list prices: {str(e)}")
        
        return all_prices
    
    async def get_variant_prices_by_market(
        self,
        variant_ids: List[str],
        market_ids: List[str] = None
    ) -> Dict[str, Dict[str, Dict]]:
        """
        Récupère les prix de variantes pour plusieurs marchés
        
        Args:
            variant_ids: Liste d'IDs de variantes
            market_ids: Liste optionnelle d'IDs de marchés (tous si None)
            
        Returns:
            Dict[market_name, Dict[variant_id, {price, compareAtPrice, currency}]]
        """
        result = {}
        
        # Récupérer tous les marchés avec leurs priceLists
        markets = await self.get_all_markets()
        
        for market in markets:
            # Filtrer par market_ids si fourni
            if market_ids and market["id"] not in market_ids and market["numericId"] not in market_ids:
                continue
            
            price_list = market.get("priceList")
            if not price_list:
                continue
            
            # Récupérer les prix de cette priceList
            prices = await self.get_price_list_prices(
                price_list["id"],
                variant_ids=variant_ids
            )
            
            # Organiser par variant
            market_prices = {}
            for p in prices:
                market_prices[p["variantId"]] = {
                    "price": p["price"],
                    "compareAtPrice": p["compareAtPrice"],
                    "currency": p["currency"]
                }
            
            if market_prices:
                result[market["name"]] = {
                    "marketId": market["id"],
                    "currency": price_list["currency"],
                    "priceListId": price_list["id"],
                    "prices": market_prices
                }
        
        return result
    
    async def update_catalog_prices(
        self, 
        price_list_id: str, 
        price_updates: List[Dict]
    ) -> Dict:
        """
        Met à jour les prix dans un catalogue
        
        Args:
            price_list_id: ID du price list (gid://shopify/PriceList/xxx)
            price_updates: Liste de {variantId, price, compareAtPrice, currencyCode}
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
        
        # Formater les prix pour l'API
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


# Instance globale
shopify_service = ShopifyService()
