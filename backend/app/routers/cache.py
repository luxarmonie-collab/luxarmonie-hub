"""
Router pour la gestion du cache des prix
"""
from fastapi import APIRouter, BackgroundTasks
from app.services.shopify import ShopifyService
from app.services.price_cache import price_cache

router = APIRouter(prefix="/api/cache", tags=["cache"])

shopify_service = ShopifyService()


@router.get("/status")
async def get_cache_status():
    """Retourne le statut du cache"""
    return price_cache.get_status()


@router.post("/refresh")
async def refresh_cache(background_tasks: BackgroundTasks):
    """
    Lance le rafraîchissement du cache en arrière-plan.
    Retourne immédiatement avec le statut.
    """
    if price_cache.is_loading:
        return {
            "success": False,
            "message": "Le cache est déjà en cours de chargement",
            "status": price_cache.get_status()
        }
    
    # Lancer le chargement en arrière-plan
    background_tasks.add_task(price_cache.load_all_prices, shopify_service)
    
    return {
        "success": True,
        "message": "Chargement du cache lancé en arrière-plan",
        "status": price_cache.get_status()
    }


@router.get("/progress")
async def get_cache_progress():
    """Retourne la progression du chargement"""
    return price_cache.load_progress
