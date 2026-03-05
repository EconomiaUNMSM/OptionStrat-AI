
import yfinance as yf
import pandas as pd
import time
import logging
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..core.black_scholes import bsm_greeks

logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

# Cargar .env de forma robusta
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

# Intentar importar Alpha Vantage
try:
    from alpha_vantage.options import Options as AVOptions
except ImportError:
    AVOptions = None

class OptionsDataManager:
    """
    Gestor de datos de Opciones (YFinance + Alpha Vantage).
    Encargado de descargar cadenas de opciones, precios spot y manejar Rate Limits.
    """
    
    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.av_api_key = os.getenv("ALPHA_VANTAGE_KEY")
        self.av_client = AVOptions(key=self.av_api_key) if (self.av_api_key and AVOptions) else None
        
        if not self.av_client:
            logger.warning("Alpha Vantage no configurado (falta API Key o librería). Usando solo YFinance.")

    def _safe_request(self, func, *args, **kwargs):
        """Envoltorio para manejar Rate Limits y pausas."""
        time.sleep(self.delay)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            if "Too Many Requests" in msg or "429" in msg:
                 logger.critical(f"RATE LIMIT (429) detectado en opciones. Deteniendo ejecución.")
                 raise ConnectionError("RATE_LIMIT_HIT")
            logger.error(f"Error en solicitud yfinance: {e}")
            raise e

    def get_spot_price(self, ticker: str) -> float:
        """Obtiene el precio actual del activo subyacente."""
        try:
            t = yf.Ticker(ticker)
            # Intentar fast_info primero (más rápido)
            price = t.fast_info.last_price
            if price is None:
                 history = t.history(period="1d")
                 if not history.empty:
                     price = history["Close"].iloc[-1]
            return price
        except Exception as e:
            logger.error(f"No se pudo obtener precio spot para {ticker}: {e}")
            return 0.0

    def get_historical_volatility(self, ticker: str, days: int = 30) -> Dict[str, float]:
        """
        Calcula Estadísticas de Volatilidad Histórica (HV) Anualizada.
        Retorna un diccionario con:
        - current_hv: Volatilidad de los últimos 'days'
        - mean_hv: Media de la HV de 30 días en el último año
        - std_hv: Desviación estándar de la HV de 30 días en el último año
        - min_hv: Mínima HV en el último año
        - max_hv: Máxima HV en el último año
        - percentile: Percentil de la HV actual (0-100)
        """
        try:
            # Descargar historico de 1 año para tener contexto estadístico
            t = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            hist = t.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 200:
                return {}

            # Calcular Retornos Logarítmicos Diarios
            import numpy as np
            hist['LogReturn'] = np.log(hist['Close'] / hist['Close'].shift(1))
            
            # Calcular HV Rolling (Ventana Móvil de 30 días)
            window = 30
            # std * sqrt(252) anualizado
            hist['RollingHV'] = hist['LogReturn'].rolling(window=window).std() * np.sqrt(252)
            
            # Limpiar NaNs iniciales
            rolling_series = hist['RollingHV'].dropna()
            
            if rolling_series.empty:
                return {}

            current_hv = rolling_series.iloc[-1]
            mean_hv = rolling_series.mean()
            std_hv = rolling_series.std()
            min_hv = rolling_series.min()
            max_hv = rolling_series.max()
            
            # Calcular Percentil de la actual HV
            percentile = (rolling_series < current_hv).mean() * 100
            
            return {
                "current_hv": float(current_hv),
                "mean_hv": float(mean_hv),
                "std_hv": float(std_hv),
                "min_hv": float(min_hv),
                "max_hv": float(max_hv),
                "percentile": float(percentile)
            }
            
        except Exception as e:
            logger.error(f"Error calculando HV Stats para {ticker}: {e}")
            return {}

    def get_risk_free_rate(self) -> float:
        """
        Obtiene la Tasa Libre de Riesgo usando el bono a 3 meses (^IRX).
        Retorna float (ej: 0.052 para 5.2%).
        """
        try:
            # ^IRX es el índice de rendimiento de T-Bill 13 semanas
            t = yf.Ticker("^IRX")
            # Usar fast_info si es posible, sino history
            rate = t.fast_info.last_price
            if rate is None or str(rate) == 'nan':
                 hist = t.history(period='1d')
                 if not hist.empty:
                     rate = hist['Close'].iloc[-1]
                 else:
                     return 0.05 # Fallback 5%
            
            # El valor viene en porcentaje (ej 4.5), convertir a decimal
            return float(rate) / 100.0
            
        except Exception as e:
            logger.warning(f"No se pudo obtener Risk Free Rate, usando 5%: {e}")
            return 0.05

    def _normalize_av_response(self, data) -> pd.DataFrame:
        """Normaliza la respuesta de Alpha Vantage (lista de dicts o dict complejo)."""
        if not data:
            return pd.DataFrame()
            
        # Caso 1: Lista de diccionarios
        if isinstance(data, list):
            return pd.DataFrame(data)
            
        # Caso 2: Diccionario con claves 'data', 'historical_options', etc.
        if isinstance(data, dict):
            for key in ["data", "historical_options", "OptionChain"]:
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
        
        return pd.DataFrame()

    def _fetch_options_av(self, ticker: str) -> pd.DataFrame:
        """Descarga opciones FULL desde Alpha Vantage con Griegas."""
        if not self.av_client:
            return pd.DataFrame()
            
        try:
            # Alpha Vantage suele retornar una tupla (data, metadata)
            # data es una lista de diccionarios con TODA la cadena
            data, meta = self.av_client.get_historical_options(symbol=ticker)
            
            df = self._normalize_av_response(data)
            
            if df.empty:
                return pd.DataFrame()

            # Mapeo de columnas (AV usa nombres raros a veces o camelCase)
            # Ej: "implied_volatility", "ImpliedVolatility", "delta", "Delta"
            
            # Normalizar nombres a minusculas para buscar
            df.columns = [c.lower() for c in df.columns]
            
            # Renombrar a nuestro estandar
            rename_map = {
                "strike": "strike",
                "type": "type",
                "expiration": "expirationDate",
                "impliedvolatility": "impliedVolatility",
                "implied_volatility": "impliedVolatility",
                "last": "lastPrice",
                "last_price": "lastPrice",
                "bid": "bid",
                "ask": "ask",
                "volume": "volume",
                "openinterest": "openInterest",
                "open_interest": "openInterest",
                # Griegas
                "delta": "delta",
                "gamma": "gamma",
                "theta": "theta",
                "vega": "vega",
                "rho": "rho"
            }
            
            # Solo renombrar las que existan
            valid_rename = {k: v for k, v in rename_map.items() if k in df.columns}
            df = df.rename(columns=valid_rename)
            
            # Asegurar compatibilidad
            if "expirationDate" in df.columns:
                df["expirationDate"] = pd.to_datetime(df["expirationDate"])

            # Filtrar columnas clave
            wanted_cols = ["strike", "type", "expirationDate", "lastPrice", "bid", "ask", 
                           "impliedVolatility", "delta", "gamma", "theta", "vega", "volume", "openInterest"]
            
            final_df = df[[c for c in wanted_cols if c in df.columns]].copy()
            
            # Asegurar tipos
            final_df["strike"] = pd.to_numeric(final_df["strike"], errors="coerce")
            final_df["lastPrice"] = pd.to_numeric(final_df["lastPrice"], errors="coerce")
            final_df["impliedVolatility"] = pd.to_numeric(final_df["impliedVolatility"], errors="coerce")
            
            # Marcar origen
            final_df["source"] = "AV"
            
            return final_df

        except Exception as e:
            logger.warning(f"Error descargando Alpha Vantage para {ticker}: {e}")
            return pd.DataFrame()

    def get_full_option_chain(self, ticker: str, min_days: int = 20, max_days: int = 60) -> pd.DataFrame:
        """
        Descarga la cadena de opciones completa.
        Prioridad: YFinance (Rápido) -> Si falta data critica -> Alpha Vantage (Rico en Griegas)
        """
       
        # 1. Intentar Alpha Vantage PRIMERO si está configurado (Mejores Griegas)
        df_av = pd.DataFrame()
        if self.av_client:
            logger.info(f"{ticker}: Intentando descargar Griegas de Alpha Vantage...")
            df_av = self._fetch_options_av(ticker)
        
        # Si AV trajo datos buenos, usémoslos como base y rellenemos con YF si hace falta
        # Pero AV a veces tiene rate limits agresivos. 
        # Estrategia Híbrida:
        # Usar YFinance para estructura (Strike, Exp, Bid/Ask) 
        # Y "Pegarle" las griegas de AV si coinciden Strike/Exp.
        
        # O SIMPLEMENTE: Si AV funciona, usar AV.
        if not df_av.empty and "delta" in df_av.columns and not df_av["delta"].isna().all():
             logger.info(f"{ticker}: Datos de Alpha Vantage obtenidos con éxito ({len(df_av)} opciones).")
             
             # Filtrar por DTE
             curr_time = pd.Timestamp.now()
             df_av['dte'] = (df_av['expirationDate'] - curr_time).dt.days
             df_av = df_av[(df_av['dte'] >= min_days) & (df_av['dte'] <= max_days)]
             
             if not df_av.empty:
                 # Calcular Mid y limpiar
                 df_av['mid'] = (df_av['bid'] + df_av['ask']) / 2
                 df_av.loc[(df_av['bid'] == 0) | (df_av['ask'] == 0), 'mid'] = df_av['lastPrice']
                 return df_av

        # 2. Fallback a YFinance (Lógica original)
        logger.info(f"{ticker}: Usando YFinance (Alpha Vantage falló o no tiene datos)...")
        t = yf.Ticker(ticker)
        
        # ... (Resto del código original de YFinance)

        try:
            expirations = t.options
        except Exception as e:
            logger.error(f"Error obteniendo vencimientos para {ticker}: {e}")
            return pd.DataFrame()

        if not expirations:
            logger.warning(f"No hay opciones disponibles para {ticker}")
            return pd.DataFrame()

        # 2. Filtrar vencimientos por DTE (Days to Expiration)
        today = datetime.now().date()
        target_expirations = []
        
        # Convertir str a date y filtrar
        for exp_str in expirations:
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                if min_days <= dte <= max_days:
                    target_expirations.append(exp_str)
            except ValueError:
                continue
                
        if not target_expirations:
            logger.warning(f"{ticker}: No se encontraron vencimientos entre {min_days} y {max_days} días.")
            return pd.DataFrame()

        all_options = []

        # 3. Descargar cadenas para cada vencimiento
        logger.info(f"{ticker}: Descargando cadenas para {len(target_expirations)} vencimientos...")
        
        for exp in target_expirations:
            # Pausa obligatoria
            time.sleep(self.delay)
            
            try:
                # yfinance returns an object with .calls and .puts DataFrames
                chain = t.option_chain(exp)
                
                # Procesar Calls
                if not chain.calls.empty:
                    calls = chain.calls.copy()
                    calls['type'] = 'call'
                    calls['expirationDate'] = exp
                    all_options.append(calls)
                    
                # Procesar Puts
                if not chain.puts.empty:
                    puts = chain.puts.copy()
                    puts['type'] = 'put'
                    puts['expirationDate'] = exp
                    all_options.append(puts)
                    
            except Exception as e:
                msg = str(e)
                if "Too Many Requests" in msg or "429" in msg:
                    raise ConnectionError("RATE_LIMIT_HIT")
                logger.warning(f"Error descargando cadena {exp} para {ticker}: {e}")
                continue

        if not all_options:
            return pd.DataFrame()

        # 4. Consolidar y Limpiar
        df = pd.concat(all_options, ignore_index=True)
        
        # Calcular DTE
        df['expirationDate'] = pd.to_datetime(df['expirationDate'])
        curr_time = pd.Timestamp.now()
        df['dte'] = (df['expirationDate'] - curr_time).dt.days

        # Calcular Mid Price (Crucial para valoración justa)
        # Si bid o ask son 0 o raros, usar lastPrice como fallback
        df['mid'] = (df['bid'] + df['ask']) / 2
        df.loc[(df['bid'] == 0) | (df['ask'] == 0), 'mid'] = df['lastPrice']
        
        # Limpiar Volatilidades nulas o cero
        if 'impliedVolatility' not in df.columns:
            df['impliedVolatility'] = 0.0
        df['impliedVolatility'] = df['impliedVolatility'].fillna(0.0)

        # CALCULAR GRIEGAS SI FALTAN (YFinance a menudo no las trae todas)
        # Necesitamos spot price para re-calcular
        spot = self.get_spot_price(ticker)
        
        # Tasa libre de riesgo DINÁMICA
        r = self.get_risk_free_rate() 

        # Iterar y calcular si falta delta o es 0 o NaN
        # A veces yfinance trae columna delta pero llena de NaNs o ceros
        need_calc = False
        if 'delta' not in df.columns:
            need_calc = True
        elif df['delta'].isna().all() or (df['delta'] == 0).all():
             need_calc = True
        
        # FORZAR CALCULO: yfinance suele traer griegas malas o incompletas (Delta si, Theta 0).
        # Mejor recalculamos SIEMPRE con nuestro motor BSM y nuestra IV/RiskFreeRate.
        need_calc = True 

        if need_calc:
            deltas, gammas, thetas, vegas = [], [], [], []
            
            for idx, row in df.iterrows():
                try:
                    T_years = max(row['dte'], 0.5) / 365.0 # Mínimo medio día para evitar div/0
                    sigma = row['impliedVolatility']
                    
                    if sigma <= 0 or T_years <= 0:
                        deltas.append(0.0); gammas.append(0.0); thetas.append(0.0); vegas.append(0.0)
                        continue

                    greeks = bsm_greeks(
                        S=spot, 
                        K=row['strike'], 
                        T=T_years, 
                        r=r, 
                        sigma=sigma, 
                        q=0.0, # Asumimos 0 dividend por ahora, TODO: Fetch Dividend Yield
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

        # Columnas finales de interés
        cols = [
            'contractSymbol', 'expirationDate', 'dte', 'strike', 'type', 
            'lastPrice', 'bid', 'ask', 'mid', 
            'volume', 'openInterest', 'impliedVolatility', 'inTheMoney',
            'delta', 'gamma', 'theta', 'vega'
        ]
        
        # Asegurar que existan (a veces yfinance cambia nombres)
        final_cols = [c for c in cols if c in df.columns]
        
        return df[final_cols]
