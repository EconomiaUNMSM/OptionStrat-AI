from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from app.data.data_manager import OptionsDataManager
import pandas as pd
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/options",
    tags=["Option Chains"],
    responses={404: {"description": "Ticker not found"}}
)

# Inicializamos el gestor en memoria
manager = OptionsDataManager()


def _calc_greeks_for_df(df: pd.DataFrame, spot: float, rate: float) -> pd.DataFrame:
    """Calcula Griegas BSM para todo el DataFrame de opciones."""
    from app.core.black_scholes import bsm_greeks

    deltas, gammas, thetas, vegas = [], [], [], []

    for _, row in df.iterrows():
        try:
            T_years = max(row.get('dte', 1), 0.5) / 365.0
            sigma = row.get('impliedVolatility', 0.0)

            if sigma <= 0 or T_years <= 0:
                deltas.append(0.0); gammas.append(0.0); thetas.append(0.0); vegas.append(0.0)
                continue

            greeks = bsm_greeks(
                S=spot,
                K=row['strike'],
                T=T_years,
                r=rate,
                sigma=sigma,
                q=0.0,
                kind=row['type']
            )

            deltas.append(greeks.get('delta', 0.0))
            gammas.append(greeks.get('gamma', 0.0))
            thetas.append(greeks.get('theta', 0.0))
            vegas.append(greeks.get('vega', 0.0))
        except Exception:
            deltas.append(0.0); gammas.append(0.0); thetas.append(0.0); vegas.append(0.0)

    df['delta'] = deltas
    df['gamma'] = gammas
    df['theta'] = thetas
    df['vega'] = vegas
    return df


@router.get("/expirations/{ticker}")
async def get_expirations(ticker: str):
    """
    Devuelve TODAS las fechas de vencimiento disponibles para un ticker.
    Ultra-rápido: solo consulta la lista, no descarga cadenas completas.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        expirations = list(t.options)

        if not expirations:
            raise HTTPException(status_code=404, detail=f"No options found for {ticker}")

        spot = manager.get_spot_price(ticker)
        rate = manager.get_risk_free_rate()

        return {
            "ticker": ticker.upper(),
            "spot_price": spot,
            "risk_free_rate": rate,
            "expirations": expirations
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo expirations para {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chain/{ticker}")
async def get_option_chain_by_expiration(
    ticker: str,
    expiration: Optional[str] = Query(None, description="Fecha de vencimiento YYYY-MM-DD")
):
    """
    Descarga la cadena de opciones para UN vencimiento específico.
    Si no se pasa 'expiration', usa el vencimiento más cercano (>= 7 días).
    """
    try:
        import yfinance as yf
        from datetime import datetime

        t = yf.Ticker(ticker)

        # Si no se dio fecha, buscar la primera expiración >= 7 días
        if not expiration:
            all_exp = list(t.options)
            today = datetime.now().date()
            for exp_str in all_exp:
                try:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                    if (exp_date - today).days >= 7:
                        expiration = exp_str
                        break
                except ValueError:
                    continue
            if not expiration and all_exp:
                expiration = all_exp[0]

        if not expiration:
            raise HTTPException(status_code=404, detail="No expirations available")

        chain = t.option_chain(expiration)

        all_options = []
        if not chain.calls.empty:
            calls = chain.calls.copy()
            calls['type'] = 'call'
            calls['expirationDate'] = expiration
            all_options.append(calls)

        if not chain.puts.empty:
            puts = chain.puts.copy()
            puts['type'] = 'put'
            puts['expirationDate'] = expiration
            all_options.append(puts)

        spot = manager.get_spot_price(ticker)
        rate = manager.get_risk_free_rate()

        if not all_options:
            return {
                "ticker": ticker.upper(),
                "spot_price": spot,
                "risk_free_rate": rate,
                "expiration": expiration,
                "chain": {"calls": [], "puts": []}
            }

        df = pd.concat(all_options, ignore_index=True)

        # DTE
        df['expirationDate'] = pd.to_datetime(df['expirationDate'])
        curr_time = pd.Timestamp.now()
        df['dte'] = (df['expirationDate'] - curr_time).dt.days

        # Mid price
        df['mid'] = (df['bid'] + df['ask']) / 2
        df.loc[(df['bid'] == 0) | (df['ask'] == 0), 'mid'] = df['lastPrice']

        # IV
        if 'impliedVolatility' not in df.columns:
            df['impliedVolatility'] = 0.0
        df['impliedVolatility'] = df['impliedVolatility'].fillna(0.0)

        # Calcular Griegas BSM
        df = _calc_greeks_for_df(df, spot, rate)

        # Serializar
        if 'expirationDate' in df.columns:
            df['expirationDate'] = df['expirationDate'].astype(str)
        if 'lastTradeDate' in df.columns:
            df['lastTradeDate'] = df['lastTradeDate'].astype(str)
        df = df.fillna(0)

        calls_out = df[df['type'] == 'call'].to_dict(orient="records")
        puts_out = df[df['type'] == 'put'].to_dict(orient="records")

        return {
            "ticker": ticker.upper(),
            "spot_price": spot,
            "risk_free_rate": rate,
            "expiration": expiration,
            "chain": {
                "calls": calls_out,
                "puts": puts_out
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en option chain para {ticker}/{expiration}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
