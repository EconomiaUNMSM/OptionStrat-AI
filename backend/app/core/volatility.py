"""
OptionGreeksEngine

Dependencias:
    pip install yfinance scipy numpy pandas matplotlib alpha-vantage

Descripción:
    Clase para calcular precio BS, griegas analíticas y por FD, invertir implied vol,
    aproximar precio por Δ-Γ-Θ-Vega-Rho y comparar con greeks "market" si están disponibles.
"""

from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
import math
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
from scipy.optimize import brentq
import warnings

# Alpha Vantage client optional
try:
    from alpha_vantage.options import Options as AVOptions
except Exception:
    AVOptions = None


class OptionGreeksEngine:
    def __init__(self, av_api_key: Optional[str] = None):
        """
        av_api_key: optional. If provided and alpha_vantage library installed,
            the engine will attempt to fetch option chains/greeks from Alpha Vantage.
        """
        self.av_api_key = av_api_key
        self.av_client = AVOptions(key=av_api_key) if (av_api_key and AVOptions is not None) else None

    # -------------------------
    # Market helpers (yfinance)
    # -------------------------
    @staticmethod
    def get_spot_yf(ticker: str) -> Optional[float]:
        """
        Return latest close price via yfinance, or None.
        """
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(period="1d")
            if h is None or h.empty:
                return None
            return float(h["Close"].iloc[-1])
        except Exception:
            return None

    @staticmethod
    def get_option_chain_yf(ticker: str, expiration: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Returns dict {"calls":df,"puts":df} for the selected expiration (first if None).
        """
        tk = yf.Ticker(ticker.upper())
        opts = tk.options
        if not opts:
            raise RuntimeError("No option expirations found for ticker in yfinance.")
        if expiration is None:
            expiration = opts[0]
        if expiration not in opts:
            raise ValueError("expiration not in available options list.")
        calls, puts = tk.option_chain(date=expiration)[:2]
        calls = calls.copy(); puts = puts.copy()
        # normalize iv column names
        if "impliedVolatility" not in calls.columns and "implied_volatility" in calls.columns:
            calls["impliedVolatility"] = calls["implied_volatility"]
            puts["impliedVolatility"] = puts["implied_volatility"]
        calls["Expiration"] = pd.to_datetime(expiration)
        puts["Expiration"] = pd.to_datetime(expiration)
        return {"calls": calls, "puts": puts}

    def get_option_row(self, ticker: str, expiration: str, strike: float, side: str = "call",
                       prefer_av: bool = False) -> Optional[pd.Series]:
        """
        Attempts to fetch the option row for given ticker/expiration/strike from Alpha Vantage (if configured)
        or yfinance. Returns a pandas Series (row) or None.
        """
        side = side.lower()
        # First try AV if requested and available
        if prefer_av and self.av_client is not None:
            try:
                raw, meta = self.av_client.get_historical_options(symbol=ticker.upper())
                # Normalization heuristics omitted here for brevity (see previous code)
                # For production, parse raw and build dataframe. Here fallback to yfinance if complex.
            except Exception:
                pass

        # Use yfinance
        chain = self.get_option_chain_yf(ticker, expiration)
        df = chain["calls"] if side.startswith("c") else chain["puts"]
        if df is None or df.empty:
            return None
        # find exact strike or nearest
        diffs = np.abs(df["strike"].astype(float) - float(strike))
        idx = diffs.idxmin()
        return df.loc[idx]

    # -------------------------
    # Black-Scholes core
    # -------------------------
    @staticmethod
    def black_scholes_price(S: float, K: float, T: float, r: float, q: float, sigma: float,
                            option_type: str = "call") -> float:
        """
        Classic Black-Scholes-Merton price for European call/put.
        Units:
          - S, K in dollars
          - T in years
          - r, q as continuous rates (e.g., 0.02)
          - sigma in decimals (0.20 = 20% annual vol)
        """
        if T <= 0:
            return float(max(0.0, (S - K) if option_type == "call" else (K - S)))
        if sigma <= 0 or math.isnan(sigma):
            raise ValueError("sigma must be positive")
        d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if option_type == "call":
            return float(S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))
        else:
            return float(K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1))

    # -------------------------
    # Implied vol inversion
    # -------------------------
    def implied_vol(self, market_price: float, S: float, K: float, T: float, r: float, q: float,
                    option_type: str = "call", bracket: Tuple[float, float] = (1e-6, 5.0),
                    tol: float = 1e-8, maxiter: int = 100) -> Optional[float]:
        """
        Invert BS price for implied volatility using Brent's method.
        Returns sigma (decimal) or None if no root found.
        bracket is (low, high) in sigma units (e.g., 1e-6 .. 5.0)
        """
        if market_price <= 0 or T <= 0:
            return None

        def f(sigma):
            try:
                return self.black_scholes_price(S, K, T, r, q, sigma, option_type) - market_price
            except Exception:
                return market_price  # safe fallback

        a, b = bracket
        fa, fb = f(a), f(b)
        # If same sign and we don't bracket, try expanding b
        if fa * fb > 0:
            # try to find sign change by exponential stepping up b
            for _ in range(10):
                b *= 2
                fb = f(b)
                if fa * fb <= 0:
                    break
            else:
                # cannot bracket
                return None
        try:
            sigma_root = brentq(f, a, b, xtol=tol, maxiter=maxiter)
            return float(sigma_root)
        except Exception:
            return None

    # -------------------------
    # Analytical Greeks (BSM)
    # -------------------------
    @staticmethod
    def greeks_analytic(S: float, K: float, T: float, r: float, q: float, sigma: float,
                        option_type: str = "call") -> Dict[str, float]:
        """
        Returns dict with:
            - delta (unitless, 0..1)
            - gamma (per $)
            - theta (per day, $)
            - vega (per 1 percentage point, i.e., per 0.01 change in sigma)
            - vega_per_point (per absolute vol point, e.g., per 1.0)
            - rho (per 1 percentage point of r)
        Notes:
            - Standard vega formula returns change in price per unit volatility (i.e. per 1.0 = 100 p.p.)
              We return both 'vega_per_point' (per 1.0) and 'vega' (per 1% = vega_per_point/100).
            - Theta is annual; we convert to per day by dividing by 365.
            - Rho is returned per 1% for easier reading (i.e., divide standard rho by 100).
        """
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"delta": np.nan, "gamma": np.nan, "theta": np.nan,
                    "vega": np.nan, "vega_per_point": np.nan, "rho": np.nan}

        d1 = (np.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        pdf1 = norm.pdf(d1)
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        N_m_d1 = norm.cdf(-d1)
        N_m_d2 = norm.cdf(-d2)

        # Delta
        if option_type == "call":
            delta = math.exp(-q * T) * N_d1
        else:
            delta = math.exp(-q * T) * (N_d1 - 1.0)

        # Gamma
        gamma = math.exp(-q * T) * pdf1 / (S * sigma * math.sqrt(T))

        # Vega per vol point (per 1.0) and per 1%:
        vega_per_point = S * math.exp(-q * T) * pdf1 * math.sqrt(T)
        vega = vega_per_point / 100.0  # per 1 percentage point (1%)

        # Theta (annual)
        if option_type == "call":
            theta_ann = (-S * math.exp(-q * T) * pdf1 * sigma / (2.0 * math.sqrt(T))
                         - r * K * math.exp(-r * T) * N_d2
                         + q * S * math.exp(-q * T) * N_d1)
        else:
            theta_ann = (-S * math.exp(-q * T) * pdf1 * sigma / (2.0 * math.sqrt(T))
                         + r * K * math.exp(-r * T) * N_m_d2
                         - q * S * math.exp(-q * T) * N_m_d1)
        theta_per_day = theta_ann / 365.0

        # Rho: sensitivity to r (standard formula per unit r); convert to per 1% (divide by 100)
        if option_type == "call":
            rho_standard = K * T * math.exp(-r * T) * N_d2
        else:
            rho_standard = -K * T * math.exp(-r * T) * N_m_d2
        rho_per_pct = rho_standard / 100.0

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "theta": float(theta_per_day),
            "vega": float(vega),
            "vega_per_point": float(vega_per_point),
            "rho": float(rho_per_pct)
        }

    # -------------------------
    # Finite Differences Greeks (fallback)
    # -------------------------
    def greeks_fd(self, S: float, K: float, T: float, r: float, q: float, sigma: float,
                  option_type: str = "call", eps_S: float = 0.01, eps_sigma: float = 0.0001, eps_t_days: float = 1.0) -> Dict[str, float]:
        """
        FD approximations for delta, gamma, theta (per day), vega (per 1%).
        eps_S in $ (small), eps_sigma absolute in vol (like 0.0001 = 0.01%)
        """
        if T <= 0:
            return {k: np.nan for k in ("delta", "gamma", "theta", "vega", "vega_per_point", "rho")}

        # Delta (central)
        price_up = self.black_scholes_price(S + eps_S, K, T, r, q, sigma, option_type)
        price_down = self.black_scholes_price(S - eps_S, K, T, r, q, sigma, option_type)
        delta = (price_up - price_down) / (2.0 * eps_S)
        # Gamma (central)
        gamma = (price_up - 2.0 * self.black_scholes_price(S, K, T, r, q, sigma, option_type) + price_down) / (eps_S ** 2)

        # Vega (per vol point)
        price_sigma_up = self.black_scholes_price(S, K, T, r, q, sigma + eps_sigma, option_type)
        price_sigma_down = self.black_scholes_price(S, K, T, r, q, sigma - eps_sigma, option_type)
        vega_per_point = (price_sigma_up - price_sigma_down) / (2.0 * eps_sigma)
        vega = vega_per_point / 100.0

        # Theta (per day): forward 1 day
        dt = eps_t_days / 365.0
        if T - dt <= 0:
            theta = (self.black_scholes_price(S, K, max(T - dt, 0.0), r, q, sigma, option_type) -
                     self.black_scholes_price(S, K, T, r, q, sigma, option_type))
            theta_per_day = theta
        else:
            price_t_minus = self.black_scholes_price(S, K, T - dt, r, q, sigma, option_type)
            theta_per_day = (price_t_minus - self.black_scholes_price(S, K, T, r, q, sigma, option_type)) / (eps_t_days)

        # Rho (per 1%): perturb r by 0.0001 (1bp) -> convert to per 1%
        eps_r = 1e-4
        price_r_up = self.black_scholes_price(S, K, T, r + eps_r, q=q, sigma=sigma, option_type=option_type)
        price_r_down = self.black_scholes_price(S, K, T, r - eps_r, q=q, sigma=sigma, option_type=option_type)
        rho_per_unit = (price_r_up - price_r_down) / (2.0 * eps_r)
        rho_per_pct = rho_per_unit / 100.0

        return {
            "delta": float(delta),
            "gamma": float(gamma),
            "theta": float(theta_per_day),
            "vega": float(vega),
            "vega_per_point": float(vega_per_point),
            "rho": float(rho_per_pct)
        }

    # -------------------------
    # Δ–Γ–Θ–Vega–Rho approximation
    # -------------------------
    def approx_price_by_greeks(self, S: float, K: float, T: float, r: float, q: float, sigma: float,
                               delta_S: float = 0.0, delta_t_days: float = 0.0, delta_sigma_abs: float = 0.0,
                               option_type: str = "call",
                               use_analytic_greeks: bool = True) -> Tuple[float, float, float, Dict[str, float]]:
        """
        Approximates new price after small shocks using greeks.
        Inputs:
            - delta_sigma_abs: absolute change in vol (e.g., -0.01 means -1 percentage point).
            - delta_t_days: integer days advanced (1 = 1 calendar day)
        Returns:
            (price_approx, price_orig, total_change, greeks_dict)
        """
        price_orig = self.black_scholes_price(S, K, T, r, q, sigma, option_type)
        if use_analytic_greeks:
            greeks = self.greeks_analytic(S, K, T, r, q, sigma, option_type)
        else:
            greeks = self.greeks_fd(S, K, T, r, q, sigma, option_type)

        # delta_S contribution
        delta = greeks["delta"]
        gamma = greeks["gamma"]
        theta = greeks["theta"]  # per day
        # vega in our dict is per 1% (vega per pct point)
        vega_per_pct = greeks["vega"]  # price change for 1 percentage point (0.01)
        # but user passes delta_sigma_abs as absolute (e.g., -0.01), so multiply by 100 if vega expects per 1%?
        # We defined vega as per 1% (i.e., per 0.01 absolute). So delta_sigma_abs should be absolute (e.g. -0.01)
        # vega contribution = vega_per_pct * (delta_sigma_abs / 0.01) = vega_per_pct * delta_sigma_abs*100
        # Simpler: let delta_sigma_in_pct_points = delta_sigma_abs * 100
        delta_sigma_pct_points = delta_sigma_abs * 100.0
        vega_contrib = vega_per_pct * delta_sigma_pct_points

        # rho: greeks['rho'] is per 1% (i.e. per 0.01), but user likely doesn't pass delta_r here.
        # total change:
        change = delta * delta_S + 0.5 * gamma * (delta_S ** 2) + theta * delta_t_days + vega_contrib

        price_approx = price_orig + change
        return price_approx, price_orig, change, greeks

    # -------------------------
    # Error surface: approximation vs true BS
    # -------------------------
    def error_surface(self, S, K, T, r, q, sigma,
                      ds_vals: np.ndarray, dσ_vals: np.ndarray,
                      option_type: str = "call",
                      use_analytic_greeks: bool = True) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Returns error matrix = price_approx - price_true for each (dS, dσ).
        - ds_vals: array of delta_S values (in $)
        - dσ_vals: array of delta_sigma absolute values (e.g., -0.05..0.05)
        """
        error = np.zeros((len(ds_vals), len(dσ_vals)), dtype=float)
        for i, dS in enumerate(ds_vals):
            for j, dσ in enumerate(dσ_vals):
                # true price after shocks: advance time 1 day for T-1/365
                T_new = max(T - 1.0 / 365.0, 0.0)
                S_new = S + dS
                sigma_new = max(1e-8, sigma + dσ)
                price_true = self.black_scholes_price(S_new, K, T_new, r, q, sigma_new, option_type)
                price_approx, _, _, _ = self.approx_price_by_greeks(S, K, T, r, q, sigma,
                                                                    delta_S=dS, delta_t_days=1.0, delta_sigma_abs=dσ,
                                                                    option_type=option_type,
                                                                    use_analytic_greeks=use_analytic_greeks)
                error[i, j] = price_approx - price_true
        return ds_vals, dσ_vals, error

    # -------------------------
    # Compare to API greeks (if AV or yfinance contain them)
    # -------------------------
    def _safe_get_numeric(self, row: pd.Series, keys: List[str]) -> Optional[float]:
        """Intenta obtener un valor numérico de 'row' probando una lista de keys (case-insensitive)."""
        if row is None:
            return None
        for k in keys:
            # check exact key then lower/upper variants
            if k in row.index and not pd.isna(row[k]):
                try:
                    return float(row[k])
                except Exception:
                    try:
                        return float(str(row[k]).replace(",", ""))
                    except Exception:
                        continue
            # try lower/upper
            kl = k.lower()
            for col in row.index:
                if str(col).lower() == kl and not pd.isna(row[col]):
                    try:
                        return float(row[col])
                    except Exception:
                        continue
        return None
    
    
    def compare_greeks_with_api(self, ticker: str, expiration: str, strike: float,
                                side: str = "call", prefer_av: bool = False) -> Dict[str, Any]:
        """
        Robust comparison between analytic/FD greeks and API-provided greeks (if any).
        Returns comprehensive dict (api_iv, inverted_iv, iv_used, market_price, analytic_greeks, fd_greeks, api_greeks, errors...).
        """
        row = self.get_option_row(ticker, expiration, strike, side, prefer_av=prefer_av)
        if row is None:
            raise RuntimeError("Option row not found for requested leg.")
    
        # Market price (safe)
        bid = self._safe_get_numeric(row, ["bid", "Bid"])
        ask = self._safe_get_numeric(row, ["ask", "Ask"])
        market_price = None
        if (bid is not None) and (ask is not None) and (ask >= bid):
            market_price = 0.5 * (bid + ask)
        else:
            # try alternatives
            market_price = self._safe_get_numeric(row, ["lastPrice", "last", "mark", "mid", "close", "LastPrice"])
    
        # API IV if present (try several keys)
        api_iv = self._safe_get_numeric(row, ["impliedVolatility", "implied_volatility", "iv", "impliedVol"])
        # spot / r / q
        spot = self.get_spot_yf(ticker)
        try:
            r = float(yf.Ticker("^IRX").history(period="1d")["Close"].iloc[-1]) / 100.0
        except Exception:
            r = 0.0
        q = self._safe_get_numeric(row, ["dividendYield", "dividend_yield", "yield"]) or 0.0
    
        # compute T
        T = self._compute_T_from_row(row)
    
        # invert IV if needed
        inverted_iv = None
        if api_iv is None and (market_price is not None) and (spot is not None):
            inverted_iv = self.implied_vol(market_price, spot, strike, T, r, q, side)
        iv_to_use = api_iv if api_iv is not None else inverted_iv
    
        # Build api_greeks dict safe (force keys exist and floats or np.nan)
        api_greeks = {}
        for g in ("delta", "gamma", "theta", "vega", "rho"):
            val = self._safe_get_numeric(row, [g, g.capitalize(), f"greeks.{g}", f"{g}_value"])
            api_greeks[g] = float(val) if val is not None else np.nan
    
        results = {
            "api_iv": float(api_iv) if api_iv is not None else None,
            "inverted_iv": float(inverted_iv) if inverted_iv is not None else None,
            "iv_used": float(iv_to_use) if iv_to_use is not None else None,
            "market_price": float(market_price) if market_price is not None else None,
            "spot": float(spot) if spot is not None else None,
            "T": float(T),
            "r": float(r),
            "q": float(q),
            "api_greeks": api_greeks
        }
    
        if iv_to_use is None:
            # cannot compute analytic greeks - return available api greeks only
            results["analytic_greeks"] = {k: np.nan for k in ("delta", "gamma", "theta", "vega", "vega_per_point", "rho")}
            results["fd_greeks"] = {k: np.nan for k in ("delta", "gamma", "theta", "vega", "vega_per_point", "rho")}
            results["errors_analytic"] = {k: np.nan for k in ("delta", "gamma", "theta", "vega", "rho")}
            results["errors_fd"] = {k: np.nan for k in ("delta", "gamma", "theta", "vega", "rho")}
            return results
    
        # compute greeks
        analytic = self.greeks_analytic(spot, strike, T, r, q, iv_to_use, option_type=side)
        fd = self.greeks_fd(spot, strike, T, r, q, iv_to_use, option_type=side)
    
        # compute errors (analytic - api) only where api has numeric value
        errors_analytic = {}
        errors_fd = {}
        for g in ("delta", "gamma", "theta", "vega", "rho"):
            a = analytic.get(g, np.nan)
            f = fd.get(g, np.nan)
            api_val = api_greeks.get(g, np.nan)
            # ensure numeric types
            a_num = float(a) if (a is not None and not pd.isna(a)) else np.nan
            f_num = float(f) if (f is not None and not pd.isna(f)) else np.nan
            api_num = float(api_val) if (api_val is not None and not pd.isna(api_val)) else np.nan
            errors_analytic[g] = (a_num - api_num) if (not np.isnan(a_num) and not np.isnan(api_num)) else np.nan
            errors_fd[g] = (f_num - api_num) if (not np.isnan(f_num) and not np.isnan(api_num)) else np.nan
    
        results.update({
            "analytic_greeks": analytic,
            "fd_greeks": fd,
            "errors_analytic": errors_analytic,
            "errors_fd": errors_fd
        })
        return results
    

    @staticmethod
    def _compute_T_from_row(row) -> float:
        """
        Extract expiration from a yfinance/AV row and compute T in years using now.
        """
        # accepts pd.Series row with 'Expiration' or 'expiration' or 'expirationDate'
        for k in ("Expiration", "expiration", "expirationDate"):
            if k in row.index and not pd.isna(row[k]):
                try:
                    exp = pd.to_datetime(row[k])
                    return float((exp - datetime.now()).total_seconds() / (365 * 24 * 3600))
                except Exception:
                    pass
        # fallback: try 'lastTradeDate' or else small T
        return 1.0 / 252.0

    # -------------------------
    # Report helpers
    # -------------------------
    def report_compare(self, compare_dict: Dict[str, Any], pretty: bool = True) -> Dict[str, Any]:
        """
        Present a robust human-readable comparison report. Handles missing values gracefully.
        Returns a dict with summary and numeric metrics (RMSE).
        """
        analytic = compare_dict.get("analytic_greeks", {})
        fd = compare_dict.get("fd_greeks", {})
        api = compare_dict.get("api_greeks", {})
        errors_a = compare_dict.get("errors_analytic", {})
        errors_f = compare_dict.get("errors_fd", {})
    
        def safe_fmt(x, fmt="{:.6f}"):
            if x is None:
                return "NA"
            try:
                if isinstance(x, (float, np.floating)) and np.isnan(x):
                    return "NA"
                return fmt.format(float(x))
            except Exception:
                return str(x)
    
        # RMSE helper (ignore nan)
        def compute_rmse_from_errs(errs: Dict[str, Any]) -> float:
            vals = [float(v) for v in errs.values() if (v is not None and not pd.isna(v))]
            if len(vals) == 0:
                return float("nan")
            return float(np.sqrt(np.mean(np.array(vals) ** 2)))
    
        metrics = {
            "rmse_analytic": compute_rmse_from_errs(errors_a),
            "rmse_fd": compute_rmse_from_errs(errors_f)
        }
    
        if pretty:
            print("\n--- GREKS COMPARISON SUMMARY ---")
            print(f"spot: {compare_dict.get('spot')}, T: {safe_fmt(compare_dict.get('T'), '{:.4f}')} y, market_price: {safe_fmt(compare_dict.get('market_price'))}")
            print(f"api_iv: {safe_fmt(compare_dict.get('api_iv'))}, inverted_iv: {safe_fmt(compare_dict.get('inverted_iv'))}, iv_used: {safe_fmt(compare_dict.get('iv_used'))}")
            print("\nAnalytic greeks (used IV):")
            for k in ("delta", "gamma", "theta", "vega", "rho"):
                print(f"  {k:6s}: {safe_fmt(analytic.get(k))} (api: {safe_fmt(api.get(k))}) err: {safe_fmt(errors_a.get(k))}")
            print("\nFD greeks:")
            for k in ("delta", "gamma", "theta", "vega", "rho"):
                print(f"  {k:6s}: {safe_fmt(fd.get(k))} (api: {safe_fmt(api.get(k))}) err: {safe_fmt(errors_f.get(k))}")
            print("\nMetrics:", {k: (v if not np.isnan(v) else "NA") for k, v in metrics.items()})
    
        return {"summary": compare_dict, "metrics": metrics}

if __name__ == "__main__":
    
    # Ejemplo Analítico
    engine = OptionGreeksEngine()
    S = engine.get_spot_yf("GC=F")
    K = 250.0
    # suponer expir 30 días
    T = 30/365
    r = 0.02
    q = 0.0
    sigma = 0.35  # asumido o extraido de chain
    price = engine.black_scholes_price(S, K, T, r, q, sigma, "call")
    greeks = engine.greeks_analytic(S, K, T, r, q, sigma, "call")
    print("price", price)
    print("greeks", greeks)
    
    
    # Ejemplo Real
    row = engine.get_option_row("GC=F", expiration="2026-01-09", strike=300, side="call")
    mid = None
    if row is not None:
        bid = row.get("bid", np.nan); ask = row.get("ask", np.nan)
        if not np.isnan(bid) and not np.isnan(ask): mid = (bid+ask)/2
        else: mid = row.get("lastPrice", None)
    iv = engine.implied_vol(mid, S, 250, T, r, q, "call")
    print("Implied vol:", iv)
    
    # Función de Aproximación
    engine = OptionGreeksEngine()
    dS_vals = np.linspace(-5, 5, 41)
    dσ_vals = np.linspace(-0.05, 0.05, 41)
    ds_vals, dσ_vals, err = engine.error_surface(S, K, T, r, q, sigma, dS_vals, dσ_vals, option_type="call")
    
    # Grafica de calor
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8,6))
    pcm = ax.pcolormesh(dσ_vals*100, ds_vals, err, cmap="RdBu_r", shading="auto")
    ax.set_xlabel("ΔVol (%)")
    ax.set_ylabel("ΔSpot ($)")
    ax.set_title("Error Aproximación Δ–Γ–Θ–Vega vs Precio True")
    fig.colorbar(pcm, label="Precio_approx − Precio_true ($)")
    plt.axhline(0,color='k'); plt.axvline(0,color='k')
    plt.show()

    engine = OptionGreeksEngine(av_api_key="TU_API_KEY_AQUI")  # si lo tienes, sino sin key usa yfinance
    cmp = engine.compare_greeks_with_api("SPY", expiration="2025-10-20", strike=660, side="call", prefer_av=True)
    report = engine.report_compare(cmp)
    