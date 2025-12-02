"""
Service Shopify GraphQL pour Luxarmonie
Gère toutes les interactions avec l'API Shopify
"""

import httpx
import os
from typing import List, Dict, Optional
import asyncio


class ShopifyService:
    """Service de connexion à Shopify via GraphQL Admin API"""
    
    def __init__(self):
        self.shop_domain = os.getenv("SHOPIFY_SHOP_DOMAIN", "")
        self.access_token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
        self.api_version = "2024-10"
        
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            
            response = await client.post(
                self.graphql_url,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    # ========================================
    # MARKETS
    # ========================================
    
    async def get_all_markets(self) -> List[Dict]:
        """Récupère tous les marchés avec leurs catalogues"""
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
                        regions {
                            ... on Country {
                                code
                                name
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
        
        all_markets = []
        has_next = True
        cursor = None
        
        while has_next:
            variables = {"first": 50}
            if cursor:
                variables["after"] = cursor
            
            result = await self.execute_query(query, variables)
            
            if "data" in result and "markets" in result["data"]:
                edges = result["data"]["markets"]["edges"]
                for edge in edges:
                    market = edge["node"]
                    # Extraire l'ID numérique du GID
                    market["numericId"] = market["id"].split("/")[-1]
                    all_markets.append(market)
                    cursor = edge["cursor"]
                
                has_next = result["data"]["markets"]["pageInfo"]["hasNextPage"]
            else:
                has_next = False
        
        return all_markets
    
    async def get_market_catalogs(self, market_id: str) -> List[Dict]:
        """Récupère les catalogues d'un marché"""
        query = """
        query GetMarketCatalogs($marketId: ID!) {
            market(id: $marketId) {
                id
                name
                catalogs(first: 10) {
                    edges {
                        node {
                            id
                            title
                            status
                        }
                    }
                }
            }
        }
        """
        
        result = await self.execute_query(query, {"marketId": market_id})
        
        if "data" in result and result["data"]["market"]:
            catalogs = result["data"]["market"]["catalogs"]["edges"]
            return [edge["node"] for edge in catalogs]
        return []
    
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
        result = await self.execute_query(query, {"id": gid})
        
        if "data" in result and result["data"]["product"]:
            product = result["data"]["product"]
            product["variants"] = [v["node"] for v in product["variants"]["edges"]]
            return product
        return None
    
    # ========================================
    # CATALOG PRICING (écriture)
    # ========================================
    
    async def update_catalog_prices(
        self, 
        catalog_id: str, 
        price_updates: List[Dict]
    ) -> Dict:
        """
        Met à jour les prix dans un catalogue
        
        Args:
            catalog_id: ID du catalogue (market)
            price_updates: Liste de {variantId, price, compareAtPrice}
        """
        # Shopify utilise priceListFixedPricesAdd pour les catalogues
        mutation = """
        mutation UpdateCatalogPrices($priceListId: ID!, $prices: [PriceListPriceInput!]!) {
            priceListFixedPricesAdd(priceListId: $priceListId, prices: $prices) {
                prices {
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
        
        result = await self.execute_query(mutation, {
            "priceListId": catalog_id,
            "prices": prices
        })
        
        return result
    
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
                    prices(first: 250) {
                        edges {
                            node {
                                variant {
                                    id
                                    sku
                                    product {
                                        title
                                    }
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
                        }
                        pageInfo {
                            hasNextPage
                        }
                    }
                }
            }
        }
        """
        
        gid = f"gid://shopify/Market/{market_id}" if not market_id.startswith("gid://") else market_id
        result = await self.execute_query(query, {"marketId": gid})
        
        if "data" in result and result["data"]["market"]:
            return result["data"]["market"]["priceList"]
        return None
    
    # ========================================
    # BULK OPERATIONS
    # ========================================
    
    async def bulk_update_prices(
        self,
        market_name: str,
        updates: List[Dict]  # [{sku, price, compareAtPrice}, ...]
    ) -> Dict:
        """
        Mise à jour en masse des prix pour un marché
        Utilise les mutations par batch pour optimiser
        """
        # D'abord, récupérer le marché et son price list
        markets = await self.get_all_markets()
        market = next((m for m in markets if m["name"] == market_name), None)
        
        if not market:
            return {"success": False, "error": f"Market '{market_name}' not found"}
        
        price_list = await self.get_catalog_price_list(market["id"])
        
        if not price_list:
            return {"success": False, "error": f"No price list for market '{market_name}'"}
        
        # TODO: Implémenter la logique de batch update
        # Pour l'instant, retourner les infos
        return {
            "success": True,
            "market": market["name"],
            "priceListId": price_list["id"],
            "updatesCount": len(updates)
        }


# Instance globale
shopify_service = ShopifyService()
