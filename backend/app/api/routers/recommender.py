from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
import logging

from app.data.data_manager import OptionsDataManager
from app.services.strategy_recommender import StrategyRecommender

router = APIRouter(
    prefix="/options/recommend",
    tags=["Options Recommender"]
)

# Instanciamos el data manager que ya traes para recolectar el spot
data_manager = OptionsDataManager()

@router.get("/{ticker}", response_model=Dict)
async def get_strategy_recommendations(
    ticker: str,
    bias: str = Query("neutral", pattern="^(bullish|neutral|bearish)$", description="Dirección del mercado"),
    risk_profile: str = Query("balanced", pattern="^(conservative|balanced|aggressive)$", description="Perfil de Riesgo (POP vs Credito)"),
    min_dte: int = Query(30, ge=1, description="Mínimo días de expiración de las patas a vender"),
    max_dte: int = Query(60, le=180, description="Días máximos a vencimiento")
):
    """
    Ruta que recomienda estrategias estructuradas utilizando la algoritmia de Theta Gang.
    1. Descarga la cadena de opciones (Chain) de yfinance.
    2. Calcula las griegas inyectadas por BSM.
    3. Construye spreads estadísticamente ventajosos según tu sesgo.
    """
    ticker = ticker.upper()
    try:
        # 1. Obtener precio spot actual
        spot = data_manager.get_spot_price(ticker)
        if spot <= 0:
            raise HTTPException(status_code=400, detail=f"No se pudo recuperar precio Spot para {ticker}")

        # 2. Obtener data cruda de fechas
        ticker_obj = yf.Ticker(ticker)
        all_expirations = ticker_obj.options
        if not all_expirations:
            raise HTTPException(status_code=404, detail="No se encontraron fechas de expiración")
            
        # 3. Filtrar por ventana DTE (Days to Expiration)
        today = date.today()
        valid_dates = []
        for exp in all_expirations:
            dte = (date.fromisoformat(exp) - today).days
            if min_dte <= dte <= max_dte:
                valid_dates.append(exp)
        
        # Fallback: si ninguna coincide con la ventana, escogemos la opción DTE ~ 45
        if not valid_dates:
            closest_45 = min(all_expirations, key=lambda x: abs((date.fromisoformat(x) - today).days - 45))
            valid_dates = [closest_45]
        
        # IMPORTANTE: Usar UNA SOLA expiración para forzar consistencia
        # (Ej: un Iron Condor DEBE tener las 4 patas en la misma fecha)
        best_exp = min(valid_dates, key=lambda x: abs((date.fromisoformat(x) - today).days - 45))
        valid_dates = [best_exp]
            
        # 4. Descargar cademas completas para las fechas objetivo y prepararlas
        dfs = []
        for exp in valid_dates:
            try:
                opt = ticker_obj.option_chain(exp)
                # Unir e inyectar Metadatos basicos para que el Recommender construya
                calls = opt.calls.copy()
                puts = opt.puts.copy()
                
                calls['optionType'] = 'call'
                puts['optionType'] = 'put'
                calls['expiration'] = exp
                puts['expiration'] = exp
                
                dfs.append(calls)
                dfs.append(puts)
            except Exception as e:
                logging.warning(f"Error descargando {exp}: {e}")
                
        if not dfs:
            raise HTTPException(status_code=500, detail="Error compilando cadenas yfinance")

        full_chain = pd.concat(dfs, ignore_index=True)
        # Limpiar datos nulos/basura
        full_chain['bid'] = full_chain['bid'].fillna(0.0)
        full_chain['ask'] = full_chain['ask'].fillna(0.0)
        full_chain['volume'] = full_chain['volume'].fillna(0)
        full_chain['openInterest'] = full_chain['openInterest'].fillna(0)
        
        # Filtro estricto de liquidez y Thresholds dinámicas
        min_oi = 50 if risk_profile != "aggressive" else 20
        min_vol = 10 if risk_profile != "aggressive" else 5
        
        full_chain = full_chain[(full_chain['openInterest'] >= min_oi) & (full_chain['volume'] >= min_vol)]
        
        if full_chain.empty:
            raise HTTPException(status_code=400, detail=f"No hay contratos con suficiente liquidez (OI >= {min_oi} y Volumen >= {min_vol}) en la fecha {valid_dates[0]}.")
            
        full_chain['mid_price'] = (full_chain['bid'] + full_chain['ask']) / 2.0
        
        # Calcular griegas usando BSM nativo directamente
        from app.core.black_scholes import bsm_greeks
        risk_free = data_manager.get_risk_free_rate()
        
        # Enriquecer Dataframe con las griegas puras (vectorizar sería ideal, pero OK para MVP)
        deltas, gammas, thetas, vegas = [], [], [], []
        for _, row in full_chain.iterrows():
            T_years = max((date.fromisoformat(row['expiration']) - today).days / 365.25, 0.001)
            iv = row['impliedVolatility'] if row['impliedVolatility'] > 0 else 0.30
            g = bsm_greeks(S=spot, K=row['strike'], T=T_years, r=risk_free, sigma=iv, kind=row['optionType'])
            deltas.append(g['delta'])
            gammas.append(g['gamma'])
            thetas.append(g['theta'])
            vegas.append(g['vega'])
        
        full_chain['delta'] = deltas
        full_chain['gamma'] = gammas
        full_chain['theta'] = thetas
        full_chain['vega'] = vegas

        # 5. Pasamos la pelota al StrategyRecommender (Matemático)
        recommendations = StrategyRecommender.recommend(full_chain, spot, bias, risk_profile)
        
        return {
            "status": "success",
            "ticker": ticker,
            "bias": bias,
            "risk_profile": risk_profile,
            "spot": spot,
            "recommendations": recommendations,
            "analyzed_expirations": valid_dates
        }

    except Exception as e:
        logging.error(f"Recommender Endpoint Crash: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
