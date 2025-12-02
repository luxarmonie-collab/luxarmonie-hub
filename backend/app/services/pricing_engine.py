"""
Moteur de calcul des prix pour Luxarmonie
Gère toutes les transformations de prix selon les règles par pays
"""

from app.config.countries import (
    COUNTRIES, 
    ENDINGS, 
    NO_DECIMAL_CURRENCIES,
    get_country_config,
    get_ending_function,
    format_price
)
from typing import List, Dict, Optional
from pydantic import BaseModel


class PriceCalculation(BaseModel):
    """Résultat d'un calcul de prix"""
    country: str
    currency: str
    original_price: float
    final_price: str
    compare_at_price: str
    discount_percentage: float
    

class PricingOperation(BaseModel):
    """Paramètres d'une opération de pricing"""
    base_adjustment: float = -0.12  # -12% par défaut
    apply_vat: bool = True
    compare_at_markup: float = 0.40  # 40% de réduction affichée
    custom_discount: Optional[float] = None  # Réduction personnalisée


class PricingEngine:
    """Moteur de calcul des prix"""
    
    def __init__(self):
        self.countries = COUNTRIES.copy()
    
    def update_exchange_rate(self, country: str, new_rate: float) -> bool:
        """Met à jour le taux de change d'un pays"""
        if country in self.countries:
            self.countries[country]["exchange_rate"] = new_rate
            return True
        return False
    
    def update_vat(self, country: str, new_vat: float) -> bool:
        """Met à jour la TVA d'un pays"""
        if country in self.countries:
            self.countries[country]["vat"] = new_vat
            return True
        return False
    
    def calculate_price(
        self, 
        base_price_eur: float, 
        country: str,
        operation: PricingOperation
    ) -> Optional[PriceCalculation]:
        """
        Calcule le prix final pour un pays donné
        
        Args:
            base_price_eur: Prix de base en EUR
            country: Nom du pays
            operation: Paramètres de l'opération
        
        Returns:
            PriceCalculation avec tous les détails
        """
        config = self.countries.get(country)
        if not config:
            return None
        
        # 1. Ajustement de base
        if config["adjustment"] == "vat" and operation.apply_vat:
            # -12% puis +TVA
            adjusted = base_price_eur * (1 + operation.base_adjustment) * (1 + config["vat"])
        else:
            # -10% simple
            adjusted = base_price_eur * 0.90
        
        # 2. Conversion devise
        converted = adjusted * config["exchange_rate"]
        
        # 3. Appliquer la terminaison psychologique
        ending_func = get_ending_function(config["ending"])
        final_price = ending_func(converted)
        
        # 4. Calculer le Compare At pour avoir exactement X% de réduction
        discount = operation.custom_discount if operation.custom_discount else operation.compare_at_markup
        compare_at_raw = final_price / (1 - discount)
        compare_at = ending_func(compare_at_raw)
        
        # 5. Calculer le % réel de réduction
        actual_discount = (compare_at - final_price) / compare_at if compare_at > 0 else 0
        
        return PriceCalculation(
            country=country,
            currency=config["currency"],
            original_price=base_price_eur,
            final_price=format_price(final_price, config["currency"]),
            compare_at_price=format_price(compare_at, config["currency"]),
            discount_percentage=round(actual_discount * 100, 1)
        )
    
    def calculate_for_countries(
        self,
        base_price_eur: float,
        countries: List[str],
        operation: PricingOperation
    ) -> List[PriceCalculation]:
        """Calcule les prix pour plusieurs pays"""
        results = []
        for country in countries:
            calc = self.calculate_price(base_price_eur, country, operation)
            if calc:
                results.append(calc)
        return results
    
    def calculate_for_all_countries(
        self,
        base_price_eur: float,
        operation: PricingOperation
    ) -> List[PriceCalculation]:
        """Calcule les prix pour tous les pays"""
        return self.calculate_for_countries(
            base_price_eur, 
            list(self.countries.keys()), 
            operation
        )
    
    def preview_bulk_update(
        self,
        products: List[Dict],  # [{sku, price, title}, ...]
        countries: List[str],
        operation: PricingOperation
    ) -> Dict:
        """
        Prévisualise une mise à jour en masse
        
        Returns:
            {
                "total_products": int,
                "total_countries": int,
                "total_updates": int,
                "preview": [...]
            }
        """
        preview = []
        
        for product in products:
            for country in countries:
                calc = self.calculate_price(
                    product["price"], 
                    country, 
                    operation
                )
                if calc:
                    preview.append({
                        "sku": product.get("sku"),
                        "title": product.get("title", ""),
                        "country": country,
                        "original_eur": product["price"],
                        "final_price": calc.final_price,
                        "compare_at": calc.compare_at_price,
                        "currency": calc.currency,
                        "discount": calc.discount_percentage
                    })
        
        return {
            "total_products": len(products),
            "total_countries": len(countries),
            "total_updates": len(preview),
            "preview": preview
        }


# Instance globale
pricing_engine = PricingEngine()
