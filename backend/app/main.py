"""
Main application entry point
Charge le cache des prix au démarrage
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers
from app.routers import pricing, products, markets
from app.routers.cache import router as cache_router

# Services
from app.services.shopify import ShopifyService
from app.services.price_cache import price_cache

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager - charge le cache au démarrage
    """
    logger.info("=== APPLICATION STARTUP ===")
    
    # Lancer le chargement du cache en arrière-plan
    shopify_service = ShopifyService()
    
    # Créer une tâche de fond pour charger le cache
    # Ne pas bloquer le démarrage du serveur
    asyncio.create_task(load_cache_background(shopify_service))
    
    logger.info("Cache loading started in background")
    logger.info("Server is ready to accept requests")
    
    yield
    
    logger.info("=== APPLICATION SHUTDOWN ===")


async def load_cache_background(shopify_service: ShopifyService):
    """Charge le cache en arrière-plan"""
    try:
        logger.info("Starting background cache load...")
        await price_cache.load_all_prices(shopify_service)
        logger.info("Background cache load completed!")
    except Exception as e:
        logger.error(f"Background cache load failed: {e}")


# Create FastAPI app
app = FastAPI(
    title="Luxarmonie Hub API",
    description="API pour la gestion des prix multi-marchés",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers WITH PREFIXES
app.include_router(pricing.router, prefix="/api/pricing")
app.include_router(products.router, prefix="/api/products")
app.include_router(markets.router, prefix="/api/markets")
app.include_router(cache_router)  # cache_router a déjà le préfixe /api/cache


@app.get("/")
async def root():
    """Health check endpoint"""
    cache_status = price_cache.get_status()
    return {
        "status": "ok",
        "service": "Luxarmonie Hub API",
        "version": "2.0.0",
        "cache": {
            "loaded": cache_status["loaded"],
            "loading": cache_status["loading"],
            "markets": cache_status["markets_count"],
            "prices": cache_status["total_prices"]
        }
    }


@app.get("/health")
async def health():
    """Health check for Railway"""
    return {"status": "healthy"}
