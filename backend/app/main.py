from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import pricing, markets, products
import os

app = FastAPI(
    title="Luxarmonie Hub API",
    description="Pricing & Management API for Luxarmonie",
    version="1.0.0"
     redirect_slashes=False
)


# CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, mettre l'URL du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(pricing.router, prefix="/api/pricing", tags=["Pricing"])
app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])

@app.get("/")
def root():
    return {"status": "ok", "app": "Luxarmonie Hub", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}
