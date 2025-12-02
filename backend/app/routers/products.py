"""
Router pour la gestion des produits Shopify
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.shopify import shopify_service
from typing import List, Optional

router = APIRouter()


@router.get("")
async def get_products(
    search: Optional[str] = Query(None, description="Recherche par titre, SKU, handle"),
    limit: int = Query(50, ge=1, le=250, description="Nombre de produits à retourner")
):
    """
    Recherche des produits
    """
    try:
        products = await shopify_service.search_products(search or "", limit)
        
        # Formatter pour le frontend
        formatted = []
        for product in products:
            formatted.append({
                "id": product["id"],
                "numericId": product["numericId"],
                "title": product["title"],
                "handle": product["handle"],
                "status": product["status"],
                "image": product.get("featuredImage", {}).get("url") if product.get("featuredImage") else None,
                "variantsCount": len(product["variants"]),
                "variants": [
                    {
                        "id": v["id"],
                        "numericId": v["numericId"],
                        "sku": v["sku"],
                        "title": v["title"],
                        "price": v["price"],
                        "compareAtPrice": v.get("compareAtPrice")
                    }
                    for v in product["variants"]
                ]
            })
        
        return {
            "total": len(formatted),
            "products": formatted
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices-by-market")
async def get_prices_by_market(
    variant_ids: str = Query(..., description="IDs des variantes séparés par des virgules"),
    market_names: Optional[str] = Query(None, description="Noms des marchés séparés par des virgules (tous si vide)")
):
    """
    Récupère les prix actuels des variantes pour chaque marché
    
    Returns:
        Dict par marché avec les prix de chaque variante
    """
    try:
        # Parser les variant_ids
        variant_id_list = [vid.strip() for vid in variant_ids.split(",") if vid.strip()]
        
        if not variant_id_list:
            raise HTTPException(status_code=400, detail="Au moins un variant_id est requis")
        
        # Convertir en GIDs si nécessaire
        gid_list = []
        for vid in variant_id_list:
            if vid.startswith("gid://"):
                gid_list.append(vid)
            else:
                gid_list.append(f"gid://shopify/ProductVariant/{vid}")
        
        # Récupérer les prix par marché
        prices_by_market = await shopify_service.get_variant_prices_by_market(gid_list)
        
        return {
            "total_markets": len(prices_by_market),
            "variant_ids": variant_id_list,
            "prices": prices_by_market
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}")
async def get_product(product_id: str):
    """
    Récupère un produit par son ID
    """
    try:
        product = await shopify_service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
        
        return {
            "id": product["id"],
            "title": product["title"],
            "handle": product["handle"],
            "status": product["status"],
            "image": product.get("featuredImage", {}).get("url") if product.get("featuredImage") else None,
            "variants": [
                {
                    "id": v["id"],
                    "sku": v["sku"],
                    "title": v["title"],
                    "price": v["price"],
                    "compareAtPrice": v.get("compareAtPrice"),
                    "inventory": v.get("inventoryQuantity")
                }
                for v in product["variants"]
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/market-prices")
async def get_product_market_prices(product_id: str):
    """
    Récupère les prix d'un produit pour tous les marchés
    """
    try:
        # Récupérer le produit
        product = await shopify_service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
        
        # Extraire les IDs des variantes
        variant_ids = [v["id"] for v in product["variants"]]
        
        # Récupérer les prix par marché
        prices_by_market = await shopify_service.get_variant_prices_by_market(variant_ids)
        
        return {
            "product_id": product_id,
            "product_title": product["title"],
            "variants": [
                {
                    "id": v["id"],
                    "title": v["title"],
                    "base_price": v["price"]
                }
                for v in product["variants"]
            ],
            "markets": prices_by_market
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-sku/{sku}")
async def get_product_by_sku(sku: str):
    """
    Recherche un produit par SKU
    """
    try:
        products = await shopify_service.search_products(f"sku:{sku}", 10)
        
        # Trouver le produit avec le bon SKU
        for product in products:
            for variant in product["variants"]:
                if variant["sku"] == sku:
                    return {
                        "found": True,
                        "product": {
                            "id": product["id"],
                            "title": product["title"],
                            "handle": product["handle"]
                        },
                        "variant": variant
                    }
        
        return {"found": False}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
