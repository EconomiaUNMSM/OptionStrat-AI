"""
OptionsSurfaceAV - Clase para construir superficies 3D de IV y griegas desde Alpha Vantage.
Requisitos:
    pip install alpha-vantage plotly yfinance
Nota:
    Alpha Vantage rate limits aplican (free tier). Pasa tu API key a la clase.
"""
from alpha_vantage.options import Options
from datetime import datetime
import pandas as pd
import numpy as np
import re
from typing import Optional, Tuple, List, Dict
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import plotly.graph_objects as go
import yfinance as yf
from sklearn.linear_model import LinearRegression  # para métricas simples de skew (opcional)
from scipy.interpolate import griddata
import plotly.graph_objects as go
import numpy as np
import pandas as pd

class OptionsSurfaceAV:
    """
    Clase para descargar y transformar datos de opciones (Alpha Vantage),
    construir mallas 3D y graficar superficies de IV y griegas.
    Guarda la petición en self.raw_data y normaliza en self.options_df.
    """

    # posibles nombres de columnas para IV/griegas entre distintos proveedores
    IV_CANDIDATES = ["impliedVolatility", "implied_volatility", "iv", "plied_volati", "IV"]
    DELTA_CAND = ["delta", "Delta"]
    GAMMA_CAND = ["gamma", "Gamma"]
    THETA_CAND = ["theta", "Theta"]
    VEGA_CAND = ["vega", "Vega"]
    RHO_CAND = ["rho", "Rho"]
    OI_CAND = ["openInterest", "open_interest", "open_interest", "openInterest"]

    def __init__(self, api_key: str, symbol: str, spot_price: Optional[float] = None, timeout: int = 30):
        """
        Inicializa la clase, realiza la petición a Alpha Vantage y normaliza los datos.
        - api_key: tu API_KEY de Alpha Vantage
        - symbol: ticker (cualquier longitud)
        - spot_price: precio spot si lo quieres fijar; si None, intentará obtenerlo vía yfinance
        """
        self.api_key = api_key
        self.symbol = symbol.upper()
        self._client = Options(key=self.api_key)
        self.raw_data = None
        self.options_df = None  # DataFrame concatenado de calls+puts con columnas normalizadas
        self.calls = None
        self.puts = None
        self.spot = spot_price if spot_price is not None else self._get_spot_price()
        self._fetch_and_prepare(timeout=timeout)

    def _get_spot_price(self) -> Optional[float]:
        """Intenta conseguir el precio spot con yfinance como fallback."""
        try:
            df = yf.Ticker(self.symbol).history(period="1d")
            if not df.empty:
                return float(df["Close"].iloc[-1])
        except Exception:
            pass
        return None

    def _fetch_and_prepare(self, timeout: int = 30):
        """Baja los datos desde Alpha Vantage y normaliza a un DataFrame homogéneo."""
        # llamada a alpha vantage - la estructura de retorno puede variar así que normalizamos
        try:
            datos, meta = self._client.get_historical_options(symbol=self.symbol)
            self.raw_data = datos
        except Exception as e:
            raise RuntimeError(f"Error al consultar Alpha Vantage: {e}")

        # Normalizar distintos esquemas de respuesta
        df = self._normalize_alpha_response(self.raw_data)

        if df is None or df.empty:
            raise ValueError("No se pudieron normalizar datos de opciones desde la respuesta de Alpha Vantage.")

        # normalizar columnas: Type, Expiration (datetime), strike (float), iv, delta, gamma, theta, vega, rho, openInterest
        df = df.copy()
        df = self._normalize_columns(df)

        # Days to expiration
        df["Expiration"] = pd.to_datetime(df["Expiration"])
        df["daysToExp"] = (df["Expiration"] - pd.Timestamp.now()).dt.days + 1
        df["strike"] = df["strike"].astype(float)

        # Guardar por tipo
        self.calls = df[df["Type"] == "call"].reset_index(drop=True)
        self.puts = df[df["Type"] == "put"].reset_index(drop=True)
        self.options_df = pd.concat([self.calls, self.puts], axis=0).reset_index(drop=True)

    def _normalize_alpha_response(self, datos) -> Optional[pd.DataFrame]:
        """
        Intenta convertir la respuesta de alpha vantage a DataFrame:
        Posibles formatos:
          - dict con keys 'calls' y 'puts' (list/dict)
          - dict con una lista de dicts
          - DataFrame-like
        """
        if datos is None:
            return None

        # Si ya es DataFrame
        if isinstance(datos, pd.DataFrame):
            return datos

        # Si es dict con 'calls'/'puts'
        if isinstance(datos, dict):
            # keys con llamadas posibles
            lower_keys = {k.lower(): k for k in datos.keys()}
            if "calls" in lower_keys or "puts" in lower_keys:
                # tomar listas y concatenar
                calls_key = lower_keys.get("calls")
                puts_key = lower_keys.get("puts")
                parts = []
                if calls_key:
                    calls = pd.DataFrame(datos[calls_key])
                    calls["Type"] = "call"
                    parts.append(calls)
                if puts_key:
                    puts = pd.DataFrame(datos[puts_key])
                    puts["Type"] = "put"
                    parts.append(puts)
                if parts:
                    return pd.concat(parts, axis=0, ignore_index=True)

            # a veces la respuesta es {'historical': [...]} o similar
            for key in datos:
                val = datos[key]
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    try:
                        return pd.DataFrame(val)
                    except Exception:
                        continue

        # Si es lista de dicts
        if isinstance(datos, list) and len(datos) > 0 and isinstance(datos[0], dict):
            return pd.DataFrame(datos)

        # No se pudo normalizar
        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza nombres: intenta detectar IV, greeks, strike, expiration y Type.
        Añade columna 'Type' si no existe, detectando 'C'/'P' en contractSymbol como fallback.
        """
        df = df.copy()

        # Lowercase keys map
        lc = {c.lower(): c for c in df.columns}

        # Strike
        strike_candidates = ["strike", "Strike", "exercisePrice", "strikePrice"]
        for s in strike_candidates:
            if s in df.columns:
                df["strike"] = df[s].astype(float)
                break

        # Expiration: buscar columnas que contengan 'expir' 'expiration' etc.
        exp_cols = [c for c in df.columns if re.search(r"expir|expiration|expiry|expirationDate", c, re.I)]
        if exp_cols:
            df["Expiration"] = pd.to_datetime(df[exp_cols[0]])
        else:
            # Fallback: intentar extraer de contractSymbol con regex YYMMDD o YYYYMMDD
            if "contractSymbol" in df.columns:
                exps = []
                for s in df["contractSymbol"].astype(str):
                    # buscar cadena de 6, 7 u 8 dígitos -> yyMMdd o yyyyMMdd
                    m = re.search(r"(\d{6,8})", s)
                    if m:
                        ds = m.group(1)
                        try:
                            if len(ds) == 6:
                                exps.append(pd.to_datetime(ds, format="%y%m%d"))
                            elif len(ds) == 8:
                                exps.append(pd.to_datetime(ds, format="%Y%m%d"))
                            else:
                                exps.append(pd.NaT)
                        except Exception:
                            exps.append(pd.NaT)
                    else:
                        exps.append(pd.NaT)
                df["Expiration"] = pd.to_datetime(exps)

        # Type (call/put)
        if "Type" not in df.columns and "type" not in df.columns:
            # intentar campo 'optionType'
            type_cols = [c for c in df.columns if re.search(r"optiontype|optType|type", c, re.I)]
            if type_cols:
                df["Type"] = df[type_cols[0]].apply(lambda x: str(x).lower().replace("option", "").strip()[:4])
                df["Type"] = df["Type"].apply(lambda x: "call" if "call" in x or x.startswith("c") else "put")
            elif "contractSymbol" in df.columns:
                # buscar una C o P cerca de la fecha (intentar heurística)
                def _detect_type(sym):
                    s = str(sym)
                    # patrón típico en muchos tickers: ...<date><C|P><strike*1000>
                    m = re.search(r"\d{6,8}([CP])", s)
                    if m:
                        return "call" if m.group(1) == "C" else "put"
                    # fallback: si contiene ' C ' o endswith C etc
                    if re.search(r"\bC\b", s) or s.endswith("C"):
                        return "call"
                    return "put"

                df["Type"] = df["contractSymbol"].apply(_detect_type)
        else:
            # ya existe
            if "Type" not in df.columns and "type" in df.columns:
                df["Type"] = df["type"].apply(lambda x: "call" if str(x).lower().startswith("c") else "put")

        # IV (buscar entre candidatos)
        iv_col = None
        for c in self.IV_CANDIDATES:
            if c in df.columns:
                iv_col = c
                break
        if iv_col:
            df["iv"] = pd.to_numeric(df[iv_col], errors="coerce")
        else:
            # Si no hay, intentar inferir de 'last' / 'mark' no es correcto; dejar NaN y el usuario decide
            df["iv"] = np.nan

        # greeks
        for cand_list, std_col in [
            (self.DELTA_CAND, "delta"),
            (self.GAMMA_CAND, "gamma"),
            (self.THETA_CAND, "theta"),
            (self.VEGA_CAND, "vega"),
            (self.RHO_CAND, "rho"),
        ]:
            found = False
            for c in cand_list:
                if c in df.columns:
                    df[std_col] = pd.to_numeric(df[c], errors="coerce")
                    found = True
                    break
            if not found:
                df[std_col] = np.nan

        # open interest
        oi_col = None
        for c in self.OI_CAND:
            if c in df.columns:
                oi_col = c
                break
        if oi_col:
            df["openInterest"] = pd.to_numeric(df[oi_col], errors="coerce")
        else:
            df["openInterest"] = np.nan

        # Asegurar columnas obligatorias
        required = ["Type", "Expiration", "strike", "iv"]
        for r in required:
            if r not in df.columns:
                raise ValueError(f"Columna requerida '{r}' no encontrada tras normalizar. Revisa el payload recibido.")

        return df

    def get_expirations(self) -> List[pd.Timestamp]:
        """Devuelve lista de expiraciones disponibles (ordenadas)."""
        return sorted(self.options_df["Expiration"].unique())

    def _build_grid(self, df: pd.DataFrame, value_col: str = "iv",
                    strikes: Optional[np.ndarray] = None,
                    days: Optional[np.ndarray] = None,
                    fill_method: str = "interpolate") -> Tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Construye mallas X (days), Y (strike), Z (values) desde df (que debe tener 'strike' y 'daysToExp').
        Retorna (X, Y, Z, pivot_df)
        fill_method: 'interpolate'|'ffill'|'nearest'|'none'
        """

        pivot = df.pivot_table(values=value_col, index="strike", columns="daysToExp")
        pivot = pivot.sort_index().sort_index(axis=1)

        # definir ejes completos si no dados
        if strikes is None:
            strikes = pivot.index.values
        if days is None:
            days = pivot.columns.values

        # reindex para que la malla sea completa
        pivot = pivot.reindex(index=strikes, columns=days)

        # rellenar según método
        if fill_method == "interpolate":
            pivot = pivot.interpolate(axis=0, limit_direction="both").interpolate(axis=1, limit_direction="both")
            pivot = pivot.fillna(method="ffill", axis=0).fillna(method="bfill", axis=0)
            pivot = pivot.fillna(method="ffill", axis=1).fillna(method="bfill", axis=1)
        elif fill_method == "ffill":
            pivot = pivot.fillna(method="ffill").fillna(method="bfill")
        elif fill_method == "nearest":
            pivot = pivot.fillna(method="ffill").fillna(method="bfill")
        elif fill_method == "none":
            pass

        X, Y = np.meshgrid(pivot.columns.values, pivot.index.values)
        Z = pivot.values
        return X, Y, Z, pivot

    def create_mesh_for_iv(self, option_type: str = "call", fill_method: str = "interpolate"):
        """Construye y devuelve mallas X (days), Y (strike), Z (iv) para 'call' o 'put'."""
        df = self.calls if option_type.lower().startswith("c") else self.puts
        if df.empty:
            raise ValueError(f"No hay datos para option_type={option_type}")
        return self._build_grid(df, value_col="iv", fill_method=fill_method)

    def create_mesh_for_greek(self, greek: str, option_type: str = "call", fill_method: str = "interpolate"):
        """
        Construye mallas para una 'greek' específica: 'delta','gamma','theta','vega','rho'
        """
        greek = greek.lower()
        if greek not in ["delta", "gamma", "theta", "vega", "rho"]:
            raise ValueError("Greek no soportada. Usa: delta,gamma,theta,vega,rho")
        df = self.calls if option_type.lower().startswith("c") else self.puts
        if df.empty:
            raise ValueError(f"No hay datos para option_type={option_type}")
        return self._build_grid(df, value_col=greek, fill_method=fill_method)

    def _plot_surface_plotly_generic(self, df: pd.DataFrame, value_col: str,
                                     title_suffix: str,
                                     method: str = "cubic",
                                     grid_resolution: tuple = (120, 120),
                                     annotate_top_n: int = 3,
                                     show_atm_trace: bool = True,
                                     renderer: str = "browser"):
        """
        Método auxiliar que crea una superficie 3D en plotly interpolando (griddata).
        - df: DataFrame con columnas 'daysToExp','strike' y value_col
        - value_col: nombre de la columna a interpolar (e.g. 'iv','delta',...)
        - method: 'cubic'|'linear'|'nearest' (cubic necesita >=16 pts y 2D espalamiento)
        - grid_resolution: (nx, ny) resolución de la malla fina
        - annotate_top_n: número de picos a anotar
        - show_atm_trace: dibuja la traza ATM si self.spot está disponible
        - renderer: plotly renderer (usamos "browser" para forzar nueva pestaña)
        Retorna el objeto plotly.Figure
        """
        # Chequeos mínimos
        if df is None or df.empty:
            raise ValueError("DataFrame vacío. No hay datos para graficar.")
    
        pts = df.dropna(subset=[value_col, "daysToExp", "strike"])
        if pts.shape[0] < 4:
            raise ValueError("Pocos puntos para interpolar la superficie (menos de 4).")
    
        # Puntos originales
        points = np.column_stack((pts["daysToExp"].values.astype(float), pts["strike"].values.astype(float)))
        values = pts[value_col].values.astype(float)
    
        # Grid fino
        days_min, days_max = pts["daysToExp"].min(), pts["daysToExp"].max()
        strike_min, strike_max = pts["strike"].min(), pts["strike"].max()
    
        nx, ny = grid_resolution
        grid_days = np.linspace(days_min, days_max, nx)
        grid_strikes = np.linspace(strike_min, strike_max, ny)
        grid_X, grid_Y = np.meshgrid(grid_days, grid_strikes)
    
        # Intentar interpolación; si falla, caer a 'linear' o 'nearest'
        chosen_method = method
        Z = None
        for try_method in [method, "linear", "nearest"]:
            try:
                Z_try = griddata(points, values, (grid_X, grid_Y), method=try_method)
                # Si resultado es todo NaN o muy incompleto, seguir intentando
                if np.all(np.isnan(Z_try)):
                    continue
                Z = Z_try
                chosen_method = try_method
                break
            except Exception:
                continue
    
        if Z is None:
            raise RuntimeError("No fue posible interpolar la superficie con griddata.")
    
        # Rellenar NaNs residuales con nearest (segundo paso)
        if np.any(np.isnan(Z)):
            Z_nearest = griddata(points, values, (grid_X, grid_Y), method="nearest")
            mask = np.isnan(Z)
            Z[mask] = Z_nearest[mask]
    
        # Crear figura plotly Surface
        surf = go.Surface(
            x=grid_X,
            y=grid_Y,
            z=Z,
            colorscale="Viridis",
            colorbar=dict(title=value_col.upper()),
            showscale=True
        )
    
        fig = go.Figure(data=[surf])
    
        # Añadir trazas ATM (por expiry) si se solicita y existe self.spot
        if show_atm_trace and hasattr(self, "spot") and self.spot is not None:
            pivot = pts.pivot_table(values=value_col, index="strike", columns="daysToExp")
            pivot = pivot.sort_index().sort_index(axis=1)
            days = pivot.columns.values
            atm_strikes = []
            atm_vals = []
            for d in days:
                col = pivot[d].dropna()
                if col.empty:
                    atm_strikes.append(np.nan)
                    atm_vals.append(np.nan)
                    continue
                k = col.index.values[np.argmin(np.abs(col.index.values - self.spot))]
                atm_strikes.append(k)
                atm_vals.append(col.loc[k])
            # Filtrar NaNs
            days_arr = np.array(list(days))[~np.isnan(atm_vals)]
            atm_strikes_arr = np.array(atm_strikes)[~np.isnan(atm_vals)]
            atm_vals_arr = np.array(atm_vals)[~np.isnan(atm_vals)]
            if days_arr.size > 0:
                fig.add_trace(go.Scatter3d(
                    x=days_arr,
                    y=atm_strikes_arr,
                    z=atm_vals_arr,
                    mode="lines+markers",
                    marker=dict(size=3),
                    line=dict(width=3, color="red"),
                    name="ATM IV trace" if value_col == "iv" else f"ATM {value_col}"
                ))
    
        # Anotar top N picos de Z (en la malla interpolada)
        flat_inds = np.argsort(np.nan_to_num(Z.flatten(), -np.inf))[::-1]
        annotated = 0
        texts_x = []
        texts_y = []
        texts_z = []
        texts_label = []
        for idx in flat_inds:
            if annotated >= annotate_top_n:
                break
            r = idx // Z.shape[1]
            c = idx % Z.shape[1]
            zval = Z[r, c]
            if np.isnan(zval):
                continue
            xval = grid_X[r, c]
            yval = grid_Y[r, c]
            texts_x.append(xval)
            texts_y.append(yval)
            texts_z.append(zval)
            texts_label.append(f"{zval:.2%}" if value_col == "iv" else f"{zval:.4f}")
            annotated += 1
        if annotated > 0:
            fig.add_trace(go.Scatter3d(
                x=texts_x,
                y=texts_y,
                z=texts_z,
                mode="markers+text",
                marker=dict(size=3, color="black"),
                text=texts_label,
                textposition="top center",
                name="Top peaks"
            ))
    
        # Layout
        fig.update_layout(
            title=f"{self.symbol} - {title_suffix} (interpolation={chosen_method})",
            scene=dict(
                xaxis=dict(title="Days to Exp"),
                yaxis=dict(title="Strike"),
                zaxis=dict(title=value_col.upper())
            ),
            margin=dict(l=0, r=0, t=50, b=0)
        )
    
        # Forzar apertura en navegador
        fig.show(renderer=renderer)
    
        return fig

    def plot_iv_surface_plotly(self,
                               option_type: str = "call",
                               method: str = "cubic",
                               grid_resolution: tuple = (120, 120),
                               annotate_top_n: int = 3,
                               show_atm_trace: bool = True,
                               renderer: str = "browser"):
        """
        Grafica la superficie de Implied Volatility solo con plotly, aplicando suavizado.
        - option_type: 'call' o 'put'
        - method: 'cubic'|'linear'|'nearest'
        - grid_resolution: (nx, ny) tamaño de malla para suavizado
        - annotate_top_n: anotar n picos
        - show_atm_trace: mostrar traza ATM si self.spot definido
        - renderer: 'browser' fuerza abrir en navegador
        """
        df = self.calls if option_type.lower().startswith("c") else self.puts
        if df is None or df.empty:
            raise ValueError("No hay datos para el tipo de opción pedido.")
        return self._plot_surface_plotly_generic(df=df, value_col="iv",
                                                title_suffix=f"IV Surface - {option_type.title()}s",
                                                method=method,
                                                grid_resolution=grid_resolution,
                                                annotate_top_n=annotate_top_n,
                                                show_atm_trace=show_atm_trace,
                                                renderer=renderer)
    
    def plot_greek_surface_plotly(self,
                                  greek: str,
                                  option_type: str = "call",
                                  method: str = "cubic",
                                  grid_resolution: tuple = (120, 120),
                                  annotate_top_n: int = 3,
                                  show_atm_trace: bool = False,
                                  renderer: str = "browser"):
        """
        Grafica una greca en 3D con plotly y suavizado.
        - greek: 'delta','gamma','theta','vega','rho'
        - option_type: 'call'|'put'
        - method, grid_resolution, annotate_top_n: ver plot_iv_surface_plotly
        - show_atm_trace: generalmente no necesario para greeks (por eso default False)
        """
        greek = greek.lower()
        if greek not in ["delta", "gamma", "theta", "vega", "rho"]:
            raise ValueError("Greek no soportada: usa delta,gamma,theta,vega,rho")
    
        df = self.calls if option_type.lower().startswith("c") else self.puts
        if df is None or df.empty:
            raise ValueError("No hay datos para el tipo de opción pedido.")
    
        # Asegurar que exista la columna de la greca
        if greek not in df.columns or df[greek].dropna().empty:
            raise ValueError(f"No se encontraron valores válidos para la greca '{greek}' en los datos.")
    
        return self._plot_surface_plotly_generic(df=df, value_col=greek,
                                                title_suffix=f"{greek.title()} Surface - {option_type.title()}s",
                                                method=method,
                                                grid_resolution=grid_resolution,
                                                annotate_top_n=annotate_top_n,
                                                show_atm_trace=show_atm_trace,
                                                renderer=renderer)


    def compute_surface_report(self, option_type: str = "call") -> Dict[str, object]:
        """
        Calcula métricas útiles como:
         - IV ATM por expiry
         - Skew simple: slope IV vs strike (normalizado por spot) por expiry (media)
         - Strikes con mayor open interest
        Retorna diccionario con resultados.
        """
        df = self.calls if option_type.lower().startswith("c") else self.puts
        report = {}
        if df.empty:
            return report

        # asegurarnos de ordenar expiries
        exps = sorted(df["Expiration"].unique())

        atm_iv = {}
        skew_by_exp = {}
        oi_top = {}

        for e in exps:
            sub = df[df["Expiration"] == e].dropna(subset=["iv", "strike"])
            if sub.empty:
                continue
            # ATM IV
            if self.spot is not None:
                k = sub["strike"].iloc[(np.abs(sub["strike"] - self.spot)).argmin()]
                atm_iv[e] = float(sub.loc[sub["strike"] == k, "iv"].iloc[0])
            else:
                atm_iv[e] = None

            # skew: regresión IV ~ moneyness (strike/spot - 1) si spot available
            if self.spot is not None and sub.shape[0] > 3:
                X = ((sub["strike"] / self.spot) - 1).values.reshape(-1,1)
                y = sub["iv"].values
                try:
                    reg = LinearRegression().fit(X, y)
                    skew_by_exp[e] = float(reg.coef_[0])
                except Exception:
                    skew_by_exp[e] = None
            else:
                skew_by_exp[e] = None

            # open interest top strikes
            if "openInterest" in sub.columns:
                top = sub.sort_values("openInterest", ascending=False).head(3)[["strike","openInterest"]].to_dict(orient="records")
                oi_top[e] = top
            else:
                oi_top[e] = []

        report["atm_iv_by_expiry"] = atm_iv
        report["skew_by_expiry"] = skew_by_exp
        report["top_oi_by_expiry"] = oi_top
        report["spot"] = self.spot
        return report

    # Método utilitario para guardar figura matplotlib
    def save_fig(self, fig, path: str):
        fig.savefig(path, dpi=300, bbox_inches="tight")

    # Método para retornar DataFrame con columnas estandarizadas
    def get_dataframe(self) -> pd.DataFrame:
        """Retorna el DataFrame estandarizado de opciones (calls+puts)."""
        return self.options_df.copy()

    # Puedes agregar métodos adicionales: export_csv, filtrar por strike/exp, generar features para ML, etc.

# ---------------------------
# Ejemplo de uso:
# ---------------------------
if __name__ == "__main__":
    # Reemplaza con tu API KEY real
    API_KEY = "TU_API_KEY_AQUI"
    ticker = "DECK"

    # instanciada tu clase previamente:
    surf = OptionsSurfaceAV(api_key="TU_API_KEY", symbol=ticker)
    
    # IV call surface con cubic smoothing
    fig_iv = surf.plot_iv_surface_plotly(option_type="call", method="nearest", grid_resolution=(150,150))
    
    # Vega surface (plots en navegador)
    fig_vega = surf.plot_greek_surface_plotly("delta", option_type="call", method="cubic", grid_resolution=(120,120))
    
    # Obtener resumen/metrics
    report = surf.compute_surface_report(option_type="call")
    print("Report (calls):")
    for k, v in report.items():
        print(k, ":", v)
