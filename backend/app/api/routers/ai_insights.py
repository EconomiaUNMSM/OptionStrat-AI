from fastapi import APIRouter
from pydantic import BaseModel
from app.schemas.strategy_models import StrategyState
from app.core.black_scholes import bsm_greeks
from typing import List, Optional
from datetime import date
import logging

from app.services.ai_analyzer import AIAnalyzerService

router = APIRouter(
    prefix="/ai",
    tags=["AI Insights & Agentic Tools"]
)

class AIInsightResponse(BaseModel):
    risk_score: int
    quick_tips: List[str]
    net_greeks: dict
    llm_analysis: str

class GreeksResponse(BaseModel):
    risk_score: int
    quick_tips: List[str]
    net_greeks: dict
    llm_analysis: Optional[str] = None


@router.post("/greeks", response_model=GreeksResponse)
async def compute_greeks_fast(state: StrategyState):
    """
    Endpoint RAPIDO que solo calcula griegas netas + risk score.
    No llama al LLM. Ideal para actualizaciones en tiempo real.
    """
    try:
        legs = state.legs
        spot = state.underlying_price
        
        if not legs:
            return {
                "risk_score": 1,
                "net_greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0},
                "quick_tips": ["Agrega opciones para comenzar el analisis."],
                "llm_analysis": None
            }

        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        today = date.today()

        for leg in legs:
            days_remaining = (leg.expiration - today).days
            T_years = max(days_remaining / 365.25, 0.002)
            sigma = max(0.30 + state.volatility_shock, 0.01)

            greeks = bsm_greeks(S=spot, K=leg.strike, T=T_years, r=0.05, sigma=sigma, kind=leg.type)
            mult = 100 * leg.qty
            if leg.action == "sell":
                mult = -mult

            net_delta += greeks['delta'] * mult
            net_gamma += greeks['gamma'] * mult
            net_theta += greeks['theta'] * mult
            net_vega += greeks['vega'] * mult

        risk = 5
        tips = []

        if net_theta < -20:
            tips.append(f"ALERTA: Riesgo de Theta acelerado. Pierdes ${round(abs(net_theta), 2)}/dia.")
            risk += 2
        elif net_theta > 20:
            tips.append(f"Ingresas ${round(net_theta, 2)}/dia por primas desgastadas (Theta positiva).")
            risk -= 1

        if abs(net_delta) > 50:
            direction = "Alcista" if net_delta > 0 else "Bajista"
            tips.append(f"Cartera apalancada: {direction} (Delta {round(net_delta, 2)}).")
            risk += 1

        if net_gamma < -10:
            tips.append("ALERTA: Gamma negativo severo (Riesgo agudo de volatilidad).")
            risk += 3

        risk = min(max(risk, 1), 10)

        return {
            "risk_score": risk,
            "net_greeks": {
                "delta": round(net_delta, 2),
                "gamma": round(net_gamma, 2),
                "theta": round(net_theta, 2),
                "vega": round(net_vega, 2)
            },
            "quick_tips": tips if tips else ["Posicion neutral. Las griegas estan estabilizadas."],
            "llm_analysis": None
        }
    except Exception as e:
        logging.error(f"Error calculando griegas rapidas: {e}")
        return {
            "risk_score": 1,
            "net_greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0},
            "quick_tips": ["Error al calcular griegas."],
            "llm_analysis": None
        }


@router.post("/insights", response_model=AIInsightResponse)
async def analyze_strategy_via_llm(state: StrategyState):
    """
    Endpoint COMPLETO con analisis LLM. Solo se llama bajo demanda del usuario.
    """
    try:
        insight = await AIAnalyzerService.analyze_strategy(state)
        return insight
    except Exception as e:
        logging.error(f"Error procesando el Insight de IA: {e}")
        return {
            "risk_score": 1,
            "net_greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0},
            "quick_tips": ["No pudimos procesar tus griegas."],
            "llm_analysis": "Error en el Agente Evaluador."
        }
