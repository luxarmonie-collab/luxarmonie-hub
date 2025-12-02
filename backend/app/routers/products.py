"""
Router pour la gestion des produits Shopify
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.shopify import shopify_service
from typing import List, Optional

router = APIRouter()


@router.get("/")
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
