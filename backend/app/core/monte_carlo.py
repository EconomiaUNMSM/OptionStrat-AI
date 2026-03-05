import math
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm


class OptionsUpsideAnalyzer:
    """
    Analizador que, dado un conjunto de tickers (yfinance), calcula:
      - potencial upside (low/medium/high) a partir de la IV del contrato más cercano
        a 'days_to_exp' (días hasta vencimiento).
      - delta proxy (probabilidad ITM aproximada).
      - expected move (porcentaje y absoluto).
      - metadata (vol, openInterest, volume, strike seleccionado, expiration).
    Uso:
        analyzer = OptionsUpsideAnalyzer(["AAPL","SPY"])
        res = analyzer.analyze_all(days_to_exp=30, option_type="call")
    """

    def __init__(self, tickers: List[str], risk_free_rate: float = None):
        """
        tickers: lista de tickers válidos para yfinance (ej: ["AAPL","NVDA"])
        risk_free_rate: tasa libre de riesgo anual en decimal (si None intenta obtener ^IRX vía yfinance),
                        si no es posible, usa 0.0.
        """
        if not isinstance(tickers, (list, tuple)):
            raise ValueError("tickers debe ser lista de strings")
        self.tickers = [t.upper() for t in tickers]
        self._rf = risk_free_rate
        # cache simple para yfinance Ticker objects y market spot values
        self._yf_cache: Dict[str, yf.Ticker] = {}
        self._spot_cache: Dict[str, float] = {}

    # -------------------------
    # Helper: market spot and rates
    # -------------------------
    def _get_ticker_obj(self, ticker: str) -> yf.Ticker:
        t = ticker.upper()
        if t not in self._yf_cache:
            self._yf_cache[t] = yf.Ticker(t)
        return self._yf_cache[t]

    def get_spot(self, ticker: str) -> Optional[float]:
        """Return most recent close price or None."""
        t = ticker.upper()
        if t in self._spot_cache:
            return self._spot_cache[t]
        try:
            tk = self._get_ticker_obj(t)
            hist = tk.history(period="1d")
            if hist is None or hist.empty:
                return None
            price = float(hist["Close"].iloc[-1])
            self._spot_cache[t] = price
            return price
        except Exception:
            return None

    def _get_risk_free_rate(self) -> float:
        """Return stored rf if set, else attempt to fetch ^IRX (3-month T-bill) from yfinance (in decimal)."""
        if self._rf is not None:
            return self._rf
        try:
            irx = yf.Ticker("^IRX").history(period="1d")["Close"].iloc[-1]
            # ^IRX quoted in percent (e.g., 3.43) -> convert to decimal
            r = float(irx) / 100.0
            self._rf = r
            return r
        except Exception:
            self._rf = 0.0
            return 0.0

    # -------------------------
    # Option chain helpers
    # -------------------------
    def _get_expirations(self, ticker: str) -> List[str]:
        """Return yfinance options expirations list (YYYY-MM-DD strings)."""
        try:
            tk = self._get_ticker_obj(ticker)
            exps = tk.options  # list of YYYY-MM-DD strings
            return list(exps)
        except Exception:
            return []

    @staticmethod
    def _days_between_dates_from_now(expiration_str: str) -> int:
        """Return integer days from now until expiration date string (YYYY-MM-DD)."""
        try:
            exp = datetime.fromisoformat(expiration_str)
        except Exception:
            exp = pd.to_datetime(expiration_str)
        delta = exp - datetime.now()
        return max(0, int(delta.total_seconds() // (24 * 3600)))

    def _choose_nearest_expiration(self, ticker: str, target_days: int) -> Optional[Tuple[str, int]]:
        """
        Return (expiration_str, actual_days) of available expirations whose days is closest to target_days.
        If no expirations return None.
        """
        exps = self._get_expirations(ticker)
        if not exps:
            return None
        # map to days
        days_map = [(exp, self._days_between_dates_from_now(exp)) for exp in exps]
        # choose min abs diff
        chosen = min(days_map, key=lambda x: abs(x[1] - target_days))
        return chosen  # (expiration_str, days_to_exp)

    def _get_option_chain(self, ticker: str, expiration: str) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Return (calls_df, puts_df) for given ticker & expiration via yfinance.
        Each df has columns as yfinance provides (including 'impliedVolatility' if present).
        """
        try:
            tk = self._get_ticker_obj(ticker)
            calls, puts = tk.option_chain(date=expiration)[:2]
            calls = calls.copy()
            puts = puts.copy()
            # normalize implied volatility name if needed
            if "impliedVolatility" not in calls.columns and "implied_volatility" in calls.columns:
                calls["impliedVolatility"] = calls["implied_volatility"]
                puts["impliedVolatility"] = puts["implied_volatility"]
            return calls, puts
        except Exception:
            return None

    # -------------------------
    # Black-Scholes helpers (for delta)
    # -------------------------
    @staticmethod
    def _bs_d1(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
        return (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    @staticmethod
    def _bs_delta(S: float, K: float, T: float, r: float, q: float, sigma: float, option_type: str = "call") -> float:
        """
        Return Black-Scholes delta (call or put).
        Delta per 1 unit (0..1 for call, -1..0 for put)
        """
        if T <= 0 or sigma <= 0:
            # payoff immediate
            if option_type == "call":
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
        d1 = OptionsUpsideAnalyzer._bs_d1(S, K, T, r, q, sigma)
        if option_type == "call":
            return math.exp(-q * T) * norm.cdf(d1)
        else:
            return math.exp(-q * T) * (norm.cdf(d1) - 1.0)

    # -------------------------
    # Public method: IV for nearest contract
    # -------------------------
    def get_iv_for_nearest_contract(
        self,
        ticker: str,
        days_to_exp: int,
        option_type: str = "call",
        strike: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Busca la expiración con días más cercana a days_to_exp, toma el strike solicitado (o ATM si None)
        y devuelve:
            {
                "ticker": ticker,
                "spot": spot,
                "expiration": expiration (YYYY-MM-DD),
                "daysToExp": days_int,
                "strike": strike_selected,
                "iv": implied_vol (decimal) or None,
                "openInterest": value or None,
                "volume": value or None,
                "type": option_type,
                "chain_calls": df_calls (if requested),
                "chain_puts": df_puts
            }
        """
        ticker = ticker.upper()
        spot = self.get_spot(ticker)
        if spot is None:
            raise RuntimeError(f"No spot available for {ticker}")

        chosen = self._choose_nearest_expiration(ticker, days_to_exp)
        if chosen is None:
            return {"error": "no options available for ticker"}

        expiration, actual_days = chosen
        chain = self._get_option_chain(ticker, expiration)
        if chain is None:
            return {"error": "could not fetch option chain for expiration", "expiration": expiration}

        calls, puts = chain
        # choose which side
        side_df = calls if option_type.lower().startswith("c") else puts

        # pick strike: if provided exact strike available, use nearest match; else ATM nearest strike
        if strike is None:
            # find strike closest to spot
            strike_arr = side_df["strike"].astype(float).values
            idx = (np.abs(strike_arr - spot)).argmin()
            strike_selected = float(strike_arr[idx])
        else:
            # pick nearest available strike
            strike_arr = side_df["strike"].astype(float).values
            idx = (np.abs(strike_arr - float(strike))).argmin()
            strike_selected = float(strike_arr[idx])

        # get the row for strike (choose calls then puts or viceversa)
        row = side_df[side_df["strike"].astype(float) == strike_selected]
        if row.empty:
            # fallback: choose nearest by index
            row = side_df.iloc[[idx]]

        # try to extract IV from the row: many yfinance chains have 'impliedVolatility' column (decimal)
        iv = None
        try:
            v = row["impliedVolatility"].iloc[0]
            iv = float(v) if (not pd.isna(v)) else None
        except Exception:
            iv = None

        # openInterest & volume if present
        oi = None
        vol = None
        if "openInterest" in row.columns:
            try:
                oi = float(row["openInterest"].iloc[0])
            except Exception:
                oi = None
        if "volume" in row.columns:
            try:
                vol = float(row["volume"].iloc[0])
            except Exception:
                vol = None

        return {
            "ticker": ticker,
            "spot": spot,
            "expiration": expiration,
            "daysToExp": actual_days,
            "strike": strike_selected,
            "iv": iv,
            "openInterest": oi,
            "volume": vol,
            "type": option_type,
            "chain_calls": calls,
            "chain_puts": puts
        }

    # -------------------------
    # Compute potential upside for a single ticker
    # -------------------------
    def compute_potential_upside_for_ticker(
        self,
        ticker: str,
        days_to_exp: int,
        option_type: str = "call",
        strike: Optional[float] = None,
        percentile_high: float = 0.84,
        percentile_low: float = 0.16
    ) -> Dict[str, Any]:
        """
        Calcula las métricas solicitadas para un ticker concreto:
         - delta (proxy prob ITM) para el contrato seleccionado
         - precio objetivo upside: low / medium / high
         - iv del contrato seleccionado
         - average expected move (market expectation)
        Notas:
         - T se calcula como daysToExp / 365
         - expected_move_pct = iv * sqrt(T)  (iv decimal)
         - expected_move_abs = spot * expected_move_pct
        """
        info = self.get_iv_for_nearest_contract(ticker, days_to_exp, option_type=option_type, strike=strike)
        if "error" in info:
            return {"ticker": ticker, "error": info["error"]}

        spot = info["spot"]
        iv = info["iv"]
        days_actual = info["daysToExp"]
        expiration = info["expiration"]
        strike_used = info["strike"]
        oi = info.get("openInterest", None)
        vol = info.get("volume", None)

        # compute T in years
        T = max(0.0, days_actual / 365.0)
        r = self._get_risk_free_rate()
        # try to get dividend yield q from yfinance info (if available)
        q = 0.0
        try:
            info_yf = self._get_ticker_obj(ticker).info
            q = float(info_yf.get("dividendYield", 0.0)) if info_yf is not None else 0.0
            if q is None:
                q = 0.0
        except Exception:
            q = 0.0

        # If iv is None, attempt to estimate iv from mid price if available (rare)
        # For now, if iv is None we set expected_move to NaN and delta to NaN
        expected_move_pct = None
        expected_move_abs = None
        delta = None

        if iv is not None and iv > 0 and T > 0:
            expected_move_pct = iv * math.sqrt(T)  # decimal e.g. 0.05 = 5%
            expected_move_abs = spot * expected_move_pct
            # compute delta for that strike using BS formula
            try:
                delta = float(self._bs_delta(spot, strike_used, T, r, q, iv, option_type=option_type))
            except Exception:
                delta = None

            # define upside price targets:
            # medium = spot + expected_move_abs
            # low = spot + 0.5*expected_move_abs
            # high = spot + 1.5*expected_move_abs
            upside_medium = spot + expected_move_abs
            upside_low = spot + 0.5 * expected_move_abs
            upside_high = spot + 1.5 * expected_move_abs

            # market avg movement: use expected_move_abs (absolute)
            market_expected_move_abs = expected_move_abs
        else:
            # fallback: try historical volatility as proxy for iv (30-day std)
            hist_proxy = None
            try:
                hist = self._get_ticker_obj(ticker).history(period="60d")["Close"].dropna()
                if len(hist) >= 5:
                    ret = hist.pct_change().dropna()
                    ann_vol = float(ret.std() * math.sqrt(252))
                    hist_proxy = ann_vol
            except Exception:
                hist_proxy = None

            if hist_proxy is not None and T > 0:
                iv_est = hist_proxy
                expected_move_pct = iv_est * math.sqrt(T)
                expected_move_abs = spot * expected_move_pct
                upside_medium = spot + expected_move_abs
                upside_low = spot + 0.5 * expected_move_abs
                upside_high = spot + 1.5 * expected_move_abs
                delta = None  # no IV to feed into BS delta
                market_expected_move_abs = expected_move_abs
                iv = iv_est
            else:
                # cannot estimate
                upside_medium = upside_low = upside_high = None
                market_expected_move_abs = None

        result = {
            "ticker": ticker,
            "spot": spot,
            "expiration": expiration,
            "daysToExp": days_actual,
            "strike": strike_used,
            "option_type": option_type,
            "iv": iv,
            "delta": delta,
            "expected_move_pct": expected_move_pct,
            "expected_move_abs": expected_move_abs,
            "market_expected_move_abs": market_expected_move_abs,
            "upside_low": upside_low,
            "upside_medium": upside_medium,
            "upside_high": upside_high,
            "openInterest": oi,
            "volume": vol
        }
        return result

    # -------------------------
    # Main method: analyze all tickers
    # -------------------------
    def analyze_all(self, days_to_exp: int, option_type: str = "call", strike: Optional[float] = None) -> Dict[str, Any]:
        """
        Ejecuta compute_potential_upside_for_ticker para cada ticker de self.tickers.
        Retorna dict: ticker -> result dict.
        """
        out: Dict[str, Any] = {}
        for t in self.tickers:
            try:
                out[t] = self.compute_potential_upside_for_ticker(t, days_to_exp, option_type=option_type, strike=strike)
            except Exception as e:
                out[t] = {"error": str(e)}
        return out


# -------------------------
# Ejemplo de uso
# -------------------------
if __name__ == "__main__":
    # Ejemplo: analiza AAPL y SPY para contrato más cercano a 30 días
    analyzer = OptionsUpsideAnalyzer(["MATX", "EOG", "INFY", "DECK"])
    summary = analyzer.analyze_all(days_to_exp=252, option_type="call")
    import json
    print(json.dumps(summary, indent=2, default=str))


