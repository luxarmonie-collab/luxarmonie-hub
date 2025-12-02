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
