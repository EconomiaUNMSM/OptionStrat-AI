import pandas as pd
from typing import List, Dict, Optional

class StrategyRecommender:
    """
    Motor nativo de recomendacion de estrategias ("Theta Gang").
    Traduce el sesgo direccional y de riesgo a estrategias matematicas con ventaja estadistica.
    """
    
    @staticmethod
    def get_risk_params(profile: str) -> Dict[str, float]:
        """Define los objetivos de Delta segun perfil de riesgo."""
        if profile == "conservative":
            return {"sell_delta": 0.15, "buy_delta": 0.05, "wing_width": 5}
        elif profile == "aggressive":
            return {"sell_delta": 0.30, "buy_delta": 0.15, "wing_width": 15}
        else:  # balanced
            return {"sell_delta": 0.20, "buy_delta": 0.10, "wing_width": 10}

    @staticmethod
    def _find_closest_strike(df: pd.DataFrame, target_delta: float) -> Optional[pd.Series]:
        """Encuentra la opcion cuyo |delta| es mas cercano al target."""
        if df.empty or 'delta' not in df.columns:
            return None
        df = df.copy()
        df['diff'] = abs(abs(df['delta']) - target_delta)
        return df.sort_values('diff').iloc[0]

    @staticmethod
    def _find_strike_at(df: pd.DataFrame, target_strike: float) -> Optional[pd.Series]:
        """Encuentra la opcion con el strike mas cercano al target_strike."""
        if df.empty:
            return None
        df = df.copy()
        df['diff'] = abs(df['strike'] - target_strike)
        return df.sort_values('diff').iloc[0]

    @staticmethod
    def construct_bull_put_spread(chain_df: pd.DataFrame, spot: float, risk_profile: str) -> Optional[Dict]:
        """Construye un Bull Put Spread (Credit Spread Alcista)"""
        risk = StrategyRecommender.get_risk_params(risk_profile)
        wing_width = risk["wing_width"]
        
        puts = chain_df[(chain_df['optionType'] == 'put') & (chain_df['strike'] < spot)].copy()
        if puts.empty or 'delta' not in puts.columns:
            return None

        # Pata Corta: vender put OTM con delta objetivo
        short_put = StrategyRecommender._find_closest_strike(puts, risk["sell_delta"])
        if short_put is None:
            return None

        # Pata Larga: comprar put mas OTM a ~wing_width de distancia
        target_long_strike = short_put['strike'] - wing_width
        long_puts = puts[puts['strike'] < short_put['strike']]
        if long_puts.empty:
            return None
        long_put = StrategyRecommender._find_strike_at(long_puts, target_long_strike)
        if long_put is None:
            return None

        return {
            "name": "Bull Put Spread",
            "type": "bull_put_spread",
            "sentiment": "bullish",
            "legs": [
                StrategyRecommender._format_leg(short_put, "sell"),
                StrategyRecommender._format_leg(long_put, "buy")
            ]
        }

    @staticmethod
    def construct_bear_call_spread(chain_df: pd.DataFrame, spot: float, risk_profile: str, 
                                     forced_width: float = None) -> Optional[Dict]:
        """Construye un Bear Call Spread (Credit Spread Bajista).
        Si forced_width se especifica, el ala tendra ese ancho exacto."""
        risk = StrategyRecommender.get_risk_params(risk_profile)
        wing_width = forced_width if forced_width else risk["wing_width"]
        
        calls = chain_df[(chain_df['optionType'] == 'call') & (chain_df['strike'] > spot)].copy()
        if calls.empty or 'delta' not in calls.columns:
            return None

        # Pata Corta: vender call OTM con delta objetivo
        short_call = StrategyRecommender._find_closest_strike(calls, risk["sell_delta"])
        if short_call is None:
            return None

        # Pata Larga: comprar call mas OTM a ~wing_width de distancia
        target_long_strike = short_call['strike'] + wing_width
        long_calls = calls[calls['strike'] > short_call['strike']]
        if long_calls.empty:
            return None
        long_call = StrategyRecommender._find_strike_at(long_calls, target_long_strike)
        if long_call is None:
            return None

        return {
            "name": "Bear Call Spread",
            "type": "bear_call_spread",
            "sentiment": "bearish",
            "legs": [
                StrategyRecommender._format_leg(short_call, "sell"),
                StrategyRecommender._format_leg(long_call, "buy")
            ]
        }

    @staticmethod
    def construct_iron_condor(chain_df: pd.DataFrame, spot: float, risk_profile: str) -> Optional[Dict]:
        """Construye un Iron Condor SIMETRICO (Neutral, Riesgo Definido).
        Ambas alas tienen el mismo ancho para balance de riesgo."""
        
        # Primero construir el Bull Put Spread
        bull_put = StrategyRecommender.construct_bull_put_spread(chain_df, spot, risk_profile)
        if not bull_put:
            return None
        
        # Calcular el ancho real del ala put
        put_short_strike = bull_put["legs"][0]["strike"]
        put_long_strike = bull_put["legs"][1]["strike"]
        put_width = abs(put_short_strike - put_long_strike)
        
        if put_width <= 0:
            return None
        
        # Forzar el Bear Call Spread al MISMO ancho que el put spread
        bear_call = StrategyRecommender.construct_bear_call_spread(
            chain_df, spot, risk_profile, forced_width=put_width
        )
        if not bear_call:
            return None

        # Validar que quedo razonablemente simetrico
        call_short_strike = bear_call["legs"][0]["strike"]
        call_long_strike = bear_call["legs"][1]["strike"]
        call_width = abs(call_long_strike - call_short_strike)
        
        # Si las alas difieren mas del 50%, rechazar
        if min(put_width, call_width) > 0:
            ratio = max(put_width, call_width) / min(put_width, call_width)
            if ratio > 1.5:
                return None

        return {
            "name": "Iron Condor",
            "type": "iron_condor",
            "sentiment": "neutral",
            "legs": bull_put["legs"] + bear_call["legs"]
        }

    @staticmethod
    def construct_short_strangle(chain_df: pd.DataFrame, spot: float, risk_profile: str) -> Optional[Dict]:
        """Construye un Short Strangle (Neutral, Riesgo Indefinido)"""
        risk = StrategyRecommender.get_risk_params(risk_profile)
        
        puts = chain_df[(chain_df['optionType'] == 'put') & (chain_df['strike'] < spot)].copy()
        calls = chain_df[(chain_df['optionType'] == 'call') & (chain_df['strike'] > spot)].copy()
        
        if puts.empty or calls.empty or 'delta' not in puts.columns:
            return None
        
        short_put = StrategyRecommender._find_closest_strike(puts, risk["sell_delta"])
        short_call = StrategyRecommender._find_closest_strike(calls, risk["sell_delta"])
        
        if short_put is None or short_call is None:
            return None
        
        return {
            "name": "Short Strangle",
            "type": "short_strangle",
            "sentiment": "neutral",
            "legs": [
                StrategyRecommender._format_leg(short_put, "sell"),
                StrategyRecommender._format_leg(short_call, "sell")
            ]
        }

    @staticmethod
    def _format_leg(row: pd.Series, action: str) -> Dict:
        """Formatea una fila del DataFrame al schema esperado por el frontend"""
        return {
            "strike": float(row['strike']),
            "type": row['optionType'],
            "action": action,
            "premium": float(row['mid_price']),
            "qty": 1,
            "expiration": row['expiration'],
            "volume": int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
            "open_interest": int(row.get('openInterest', 0)) if pd.notna(row.get('openInterest')) else 0
        }

    @staticmethod
    def validate_strategy(strategy: Dict, spot: float) -> Dict:
        """Calcula metricas clave como Max Loss, Net Premium, POP y ROC."""
        legs = strategy["legs"]
        
        total_credit = 0.0
        for leg in legs:
            cost = leg["premium"] * leg["qty"] * 100
            if leg["action"] == "sell":
                total_credit += cost
            else:
                total_credit -= cost
            
        max_loss = 0.0
        buying_power = 0.0
        
        sell_legs = [l for l in legs if l["action"] == "sell"]
        buy_legs = [l for l in legs if l["action"] == "buy"]
        
        # 4 Patas: Iron Condor
        if len(legs) == 4 and len(sell_legs) == 2 and len(buy_legs) == 2:
            put_strikes = [l["strike"] for l in legs if l["type"] == "put"]
            call_strikes = [l["strike"] for l in legs if l["type"] == "call"]
            
            put_width = abs(put_strikes[0] - put_strikes[1]) * 100
            call_width = abs(call_strikes[0] - call_strikes[1]) * 100
            
            wider_spread = max(put_width, call_width)
            max_loss = wider_spread - total_credit
            buying_power = max_loss
            
        # 2 Patas: Vertical Spread
        elif len(legs) == 2 and len(sell_legs) == 1 and len(buy_legs) == 1:
            width = abs(legs[0]["strike"] - legs[1]["strike"]) * 100
            max_loss = width - total_credit
            buying_power = max_loss
            
        # 2 Patas: Short Strangle
        elif len(legs) == 2 and len(sell_legs) == 2:
            max_loss = float('inf')
            buying_power = spot * 0.20 * 100
            
        roc = (total_credit / buying_power * 100) if buying_power > 0 and max_loss > 0 else 0
        
        strategy["metrics"] = {
            "net_premium": round(total_credit, 2),
            "max_loss": round(max_loss, 2) if max_loss != float('inf') else "Unlimited",
            "margin_req": round(buying_power, 2),
            "roc_percent": round(roc, 2)
        }
        
        return strategy

    @classmethod
    def recommend(cls, chain_df: pd.DataFrame, spot: float, bias: str, risk_profile: str) -> List[Dict]:
        """
        Punto de entrada principal. Genera la lista de recomendaciones.
        bias: "bullish", "neutral", "bearish"
        risk_profile: "conservative", "balanced", "aggressive"
        """
        candidates = []
        
        if bias == "bullish":
            strat = cls.construct_bull_put_spread(chain_df, spot, risk_profile)
            if strat:
                candidates.append(cls.validate_strategy(strat, spot))
                
        elif bias == "bearish":
            strat = cls.construct_bear_call_spread(chain_df, spot, risk_profile)
            if strat:
                candidates.append(cls.validate_strategy(strat, spot))
                
        elif bias == "neutral":
            # Para neutral, intentamos IC primero
            ic = cls.construct_iron_condor(chain_df, spot, risk_profile)
            if ic:
                candidates.append(cls.validate_strategy(ic, spot))
            
            # Y un strangle si el perfil es agresivo
            if risk_profile == "aggressive":
                strangle = cls.construct_short_strangle(chain_df, spot, risk_profile)
                if strangle:
                    candidates.append(cls.validate_strategy(strangle, spot))

        # Filtrar invalidas o sin credito
        valid_candidates = [c for c in candidates if c["metrics"]["net_premium"] > 0]
                
        # Ordenar por ROC (descendente)
        valid_candidates.sort(key=lambda x: x["metrics"]["roc_percent"], reverse=True)
        return valid_candidates
