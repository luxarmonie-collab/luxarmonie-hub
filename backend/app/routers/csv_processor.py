"""
Router pour le traitement CSV des prix Matrixify
Upload CSV → Modification → Download CSV modifié
Format de sortie compatible Matrixify : Price / [Pays], Compare At Price / [Pays]
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import pandas as pd
import math
import random
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/csv", tags=["csv"])


# ========================================
# FONCTIONS DE TERMINAISON PSYCHOLOGIQUE
# ========================================

def round_99(price: float) -> float:
    """Low-context: .99"""
    return float(math.floor(price)) + 0.99

def round_95(price: float) -> float:
    """Allemagne, Autriche, Suisse: .95"""
    return float(math.floor(price)) + 0.95

def round_00(price: float) -> float:
    """High-context: .00"""
    return float(round(price))

def round_9_int(price: float) -> float:
    """Moyen-Orient: entier finissant en 9"""
    base = int(price)
    last = base % 10
    if last == 9:
        return float(base)
    elif last < 9:
        return float(base - last + 9) if base >= 10 else float(9)
    return float(base - 1)

def round_000(price: float) -> float:
    """Grandes devises: milliers"""
    thousands = round(price / 1000)
    return float(max(thousands, 1) * 1000)

def round_990(price: float) -> float:
    """HUF, CZK, RSD: en 990/90/9"""
    base = int(price)
    if base >= 10000:
        return float((base // 1000) * 1000 + 990)
    elif base >= 1000:
        return float((base // 100) * 100 + 90)
    else:
        return float((base // 10) * 10 + 9)

def round_kr(price: float) -> float:
    """Scandinave: multiples de 5"""
    return float(round(price / 5) * 5)


# Mapping pays → fonction
COUNTRY_ROUNDING = {
    # .99
    'France': round_99, 'USA': round_99, 'UK': round_99, 'Canada': round_99,
    'Australie': round_99, 'Nouvelle': round_99, 'Belgique': round_99,
    'Espagne': round_99, 'Pays-Bas': round_99, 'Luxembourg': round_99,
    'ESTONIE': round_99, 'Grèce': round_99, 'Irlande': round_99,
    'Portugal': round_99, 'Croatie': round_99, 'Finlande': round_99,
    'Pologne': round_99, 'Mexique': round_99, 'Israël': round_99,
    'Pérou': round_99, 'Bolivie': round_99, 'Guatemala': round_99,
    'Honduras': round_99, 'Turquie': round_99, 'République Dominique': round_99,
    
    # .95
    'Allemagne': round_95, 'Autriche': round_95, 'Suisse': round_95,
    
    # .00
    'Italie': round_00, 'Brésil': round_00, 'Honk Hong': round_00,
    'SINGAPOUR': round_00, 'Argentine': round_00, 'Uruguay': round_00,
    'Costa Rica': round_00, 'Afrique du Sud': round_00, 'Équateur': round_00,
    'Bahrëin': round_00, 'sal': round_00, 'Autres': round_00,
    'Norvège': round_00,
    
    # Scandinave
    'Danemark': round_kr, 'Suède': round_kr,
    
    # 990
    'Hongrie': round_990, 'République tchèque': round_990, 'Serbie': round_990,
    
    # 9 entier
    'Arabie Saoudite': round_9_int, 'Émirats Arabes Unis': round_9_int, 'Qatar': round_9_int,
    
    # Milliers
    'Chili': round_000, 'Colombie': round_000, 'Paraguay': round_000,
}

def get_rounding_function(country: str):
    return COUNTRY_ROUNDING.get(country, round_99)


def detect_csv_format(df: pd.DataFrame) -> str:
    """
    Détecte le format du CSV uploadé
    Returns: 'matrixify' ou 'ablestar'
    """
    cols = df.columns.tolist()
    
    # Format Matrixify: "Price / France", "Compare At Price / France"
    if any('Price / ' in col for col in cols):
        return 'matrixify'
    
    # Format Ablestar: "France price", "France compare-at price"
    if any(' price' in col for col in cols):
        return 'ablestar'
    
    return 'unknown'


def extract_country_from_column(col: str, csv_format: str) -> tuple:
    """
    Extrait le nom du pays et le type de colonne
    Returns: (country, column_type) ou (None, None)
    """
    if csv_format == 'matrixify':
        if col.startswith('Price / '):
            return col.replace('Price / ', ''), 'price'
        elif col.startswith('Compare At Price / '):
            return col.replace('Compare At Price / ', ''), 'compare_at'
    elif csv_format == 'ablestar':
        if ' compare-at price' in col:
            return col.replace(' compare-at price', ''), 'compare_at'
        elif ' price' in col:
            return col.replace(' price', ''), 'price'
    
    return None, None


def process_csv(
    df: pd.DataFrame,
    adjustment_pct: float = 0,
    compare_at_pct: float = 40,
    promo_mode: bool = False,
    promo_catalog_pct: float = 50,
    promo_min: float = 10,
    promo_max: float = 40,
    remove_promos: bool = False
) -> pd.DataFrame:
    """
    Traite le CSV avec les modifications demandées
    """
    csv_format = detect_csv_format(df)
    logger.info(f"Detected CSV format: {csv_format}")
    
    # Trouver les colonnes de prix selon le format
    if csv_format == 'matrixify':
        price_cols = [col for col in df.columns if col.startswith('Price / ')]
    else:  # ablestar
        price_cols = [col for col in df.columns if ' price' in col and 'compare' not in col]
    
    logger.info(f"Processing {len(df)} variants, {len(price_cols)} countries")
    
    if remove_promos:
        # Supprimer les promos
        for price_col in price_cols:
            country, _ = extract_country_from_column(price_col, csv_format)
            if csv_format == 'matrixify':
                compare_col = f"Compare At Price / {country}"
            else:
                compare_col = f"{country} compare-at price"
            
            for idx in df.index:
                compare_at = df.at[idx, compare_col] if compare_col in df.columns else None
                current_price = df.at[idx, price_col]
                
                if pd.notna(compare_at) and pd.notna(current_price):
                    if float(compare_at) > float(current_price):
                        df.at[idx, price_col] = compare_at
                        if compare_col in df.columns:
                            df.at[idx, compare_col] = pd.NA
        
        logger.info("Promos removed")
        
    elif promo_mode:
        # Promos aléatoires
        total_variants = len(df)
        promo_count = int(total_variants * (promo_catalog_pct / 100))
        selected_indices = random.sample(list(df.index), promo_count)
        
        variant_discounts = {}
        for idx in selected_indices:
            discount = random.uniform(promo_min, promo_max)
            variant_discounts[idx] = round(discount)
        
        for idx in selected_indices:
            discount_pct = variant_discounts[idx]
            reduction_factor = 1 - (discount_pct / 100)
            
            for price_col in price_cols:
                country, _ = extract_country_from_column(price_col, csv_format)
                if csv_format == 'matrixify':
                    compare_col = f"Compare At Price / {country}"
                else:
                    compare_col = f"{country} compare-at price"
                
                current_price = df.at[idx, price_col]
                
                if pd.notna(current_price) and float(current_price) > 0:
                    compare_at = float(current_price)
                    round_func = get_rounding_function(country)
                    new_price = round_func(compare_at * reduction_factor)
                    
                    df.at[idx, price_col] = new_price
                    if compare_col in df.columns:
                        df.at[idx, compare_col] = compare_at
        
        logger.info(f"Random promos applied: {promo_count} variants")
        
    elif adjustment_pct != 0:
        # Ajustement global
        factor = 1 + (adjustment_pct / 100)
        compare_at_factor = 1 + (compare_at_pct / 100)
        
        for price_col in price_cols:
            country, _ = extract_country_from_column(price_col, csv_format)
            if csv_format == 'matrixify':
                compare_col = f"Compare At Price / {country}"
            else:
                compare_col = f"{country} compare-at price"
            
            round_func = get_rounding_function(country)
            
            for idx in df.index:
                current_price = df.at[idx, price_col]
                
                if pd.notna(current_price) and float(current_price) > 0:
                    new_price_raw = float(current_price) * factor
                    new_price = round_func(new_price_raw)
                    compare_at = round_func(new_price * compare_at_factor)
                    
                    df.at[idx, price_col] = new_price
                    if compare_col in df.columns:
                        df.at[idx, compare_col] = compare_at
        
        logger.info(f"Adjustment {adjustment_pct:+.0f}% applied")
    
    return df


def convert_to_matrixify_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit un CSV au format Ablestar vers le format Matrixify
    Input:  Variant ID, France price, France compare-at price, ...
    Output: Variant ID, Price / France, Compare At Price / France, ...
    """
    csv_format = detect_csv_format(df)
    
    if csv_format == 'matrixify':
        # Déjà au bon format, juste supprimer les colonnes Price et Compare At Price de base si présentes
        cols_to_drop = []
        if 'Price' in df.columns:
            cols_to_drop.append('Price')
        if 'Compare At Price' in df.columns:
            cols_to_drop.append('Compare At Price')
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
        return df
    
    # Convertir depuis le format Ablestar
    new_data = {}
    
    for col in df.columns:
        if col == 'Variant ID':
            new_data['Variant ID'] = df[col]
        elif col in ['Price', 'Compare-at Price']:
            # Ignorer les colonnes du marché de base
            pass
        elif ' compare-at price' in col:
            country = col.replace(' compare-at price', '')
            new_data[f'Compare At Price / {country}'] = df[col]
        elif ' price' in col:
            country = col.replace(' price', '')
            new_data[f'Price / {country}'] = df[col]
    
    return pd.DataFrame(new_data)


@router.post("/analyze")
async def analyze_csv(file: UploadFile = File(...)):
    """
    Analyse le CSV uploadé et retourne les infos
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        csv_format = detect_csv_format(df)
        
        # Trouver les pays selon le format
        if csv_format == 'matrixify':
            price_cols = [col for col in df.columns if col.startswith('Price / ')]
            countries = [col.replace('Price / ', '') for col in price_cols]
        else:
            price_cols = [col for col in df.columns if ' price' in col and 'compare' not in col]
            countries = [col.replace(' price', '') for col in price_cols]
        
        return {
            "success": True,
            "filename": file.filename,
            "variants_count": len(df),
            "countries_count": len(countries),
            "countries": countries,
            "columns": list(df.columns)[:20],
            "detected_format": csv_format
        }
    except Exception as e:
        logger.error(f"CSV analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process")
async def process_csv_endpoint(
    file: UploadFile = File(...),
    adjustment: float = Form(0),
    compare_at: float = Form(40),
    promo_mode: bool = Form(False),
    promo_catalog: float = Form(50),
    promo_min: float = Form(10),
    promo_max: float = Form(40),
    remove_promos: bool = Form(False)
):
    """
    Traite le CSV et retourne le fichier modifié au format Matrixify
    """
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        logger.info(f"Processing CSV: {len(df)} rows, adjustment={adjustment}%, compare_at={compare_at}%")
        
        # Traiter les modifications
        df_modified = process_csv(
            df,
            adjustment_pct=adjustment,
            compare_at_pct=compare_at,
            promo_mode=promo_mode,
            promo_catalog_pct=promo_catalog,
            promo_min=promo_min,
            promo_max=promo_max,
            remove_promos=remove_promos
        )
        
        # Convertir au format Matrixify pour l'export
        df_matrixify = convert_to_matrixify_format(df_modified)
        
        # Générer le CSV de sortie
        output = io.StringIO()
        df_matrixify.to_csv(output, index=False)
        output.seek(0)
        
        # Nom du fichier de sortie
        if remove_promos:
            suffix = "_sans_promos"
        elif promo_mode:
            suffix = f"_promos_{int(promo_catalog)}pct"
        elif adjustment != 0:
            suffix = f"_{'+' if adjustment > 0 else ''}{int(adjustment)}pct"
        else:
            suffix = "_modified"
        
        original_name = file.filename.replace('.csv', '')
        output_filename = f"{original_name}{suffix}_MATRIXIFY.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"CSV processing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def csv_info():
    """Infos sur le module CSV"""
    return {
        "module": "CSV Price Modifier",
        "supported_countries": len(COUNTRY_ROUNDING),
        "output_format": "Matrixify compatible",
        "features": [
            "Ajustement global (+/- %)",
            "Compare-at automatique",
            "Promos aléatoires",
            "Suppression des promos",
            "Terminaisons psychologiques par pays",
            "Auto-détection format (Ablestar/Matrixify)",
            "Export format Matrixify"
        ]
    }
