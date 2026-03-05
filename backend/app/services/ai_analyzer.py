from app.schemas.strategy_models import StrategyState
from app.core.black_scholes import bsm_greeks
from datetime import date
import os
import logging
import litellm
from dotenv import load_dotenv

load_dotenv()

# Obtener configuracion AI de .env
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
if AI_PROVIDER == "openrouter":
    MODEL = os.getenv("DEFAULT_CHAT_MODEL", "openrouter/free")
else:
    MODEL = os.getenv("OPENAI_DEFAULT_CHAT_MODEL", "gpt-4o")

logger = logging.getLogger(__name__)


class AIAnalyzerService:

    @staticmethod
    async def _format_market_context(context_dict: dict) -> str:
        """Formatea el diccionario del Market Context para el LLM, de manera segura."""
        if not context_dict:
            return "Datos de mercado no disponibles."
        
        score_val = context_dict.get("sentiment_score")
        score = float(score_val) if score_val is not None else 0.0
        direction = "Bullish" if score > 0.05 else ("Bearish" if score < -0.05 else "Neutral")
        
        txt = (
            f"**Fundamentals & Analistas:**\n"
            f"- Spot Price: ${context_dict.get('current_price') or 'N/A'}\n"
            f"- Target Analyst (Mean): ${context_dict.get('target_mean') or 'N/A'} (Recomendacion: {context_dict.get('recommendation_key') or 'N/A'})\n"
            f"- P/E Forward: {context_dict.get('forward_pe') or 'N/A'}\n\n"
            
            f"**Sentimiento de Redes & Noticias (VaderScore):**\n"
            f"- Algorithmic Sentiment: {score:.2f} ({direction})\n"
            f"- Insiders Flow: {context_dict.get('insider_purchases') or 0} Compras vs {context_dict.get('insider_sales') or 0} Ventas\n"
        )
        
        recent_news = context_dict.get("recent_news")
        if recent_news and isinstance(recent_news, list):
            txt += "- Titulares Recientes:\n"
            for n in recent_news[:4]:
                txt += f"  * {n}\n"
        
        return txt

    @staticmethod
    async def _call_llm(ticker: str, greeks_summary: str, market_context: str, legs_summary: str) -> str:
        """Llama a LiteLLM UNA sola vez con todo el contexto pre-armado."""
        try:
            import asyncio

            response = await asyncio.wait_for(
                litellm.acompletion(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un 'Options Analyst Senior', experto financiero didactico asesorando al usuario.\n"
                                "IMPORTANTE SOBRE LAS GRIEGAS: Los datos estan expresados como **Position Greeks (Dolares Totales)**, "
                                "ya multiplicados x100 por el tamano estandar del contrato y por la cantidad de contratos.\n"
                                "Ejemplo: Un Delta de +16.09 significa que la posicion entera ganara $16.09 USD en total por cada $1 que el subyacente suba. "
                                "NUNCA asumas que el delta fraccional por contrato excedio la unidad.\n\n"
                                "REGLAS DE ANALISIS:\n"
                                "1. Analiza el 'DATOS DE MERCADO EN VIVO' (que incluye Sentimiento Algoritmico Vader, Targets de Analistas e Insiders) cruzandolo con la liquidez (Volumen/Interes Abierto) de la lista de Opciones armadas.\n"
                                "2. Explica brevemente si la estrategia elegida tiene sentido y probabilidad matematica considerando el Sentimiento de Noticias actual en contraste al riesgo de la posicion (delta, gamma, theta).\n"
                                "3. Manten el veredicto enfocado, limitandote a un maximo estricto de 2 parrafos impactantes y en espanol fluido, sin usar jerga informatica."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Ticker: {ticker}\n\n"
                                f"DATOS DE MERCADO EN VIVO:\n{market_context}\n\n"
                                f"ESTRATEGIA (CONTRATOS):\n{legs_summary}\n\n"
                                f"GRIEGAS NETAS DEL PORTAFOLIO EN USD (POSITION GREEKS):\n{greeks_summary}\n\n"
                                f"De acuerdo a estos datos, analiza mi posicion considerando el volumen/open interest de los contratos combinados con las ultimas noticias."
                            )
                        }
                    ]
                ),
                timeout=90.0
            )

            return response.choices[0].message.content or "Analisis completado."

        except Exception as e:
            logger.error(f"Error LiteLLM: {e}")
            return f"El analisis de IA no pudo completarse ({type(e).__name__}). Revisa tus griegas netas manualmente."

    @staticmethod
    async def analyze_strategy(state: StrategyState) -> dict:
        """Calcula el riesgo matematico y orquesta la llamada al LLM."""
        legs = state.legs
        spot = state.underlying_price

        if not legs:
            return {
                "risk_score": 1,
                "net_greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0},
                "quick_tips": ["Agrega opciones a tu estrategia para comenzar el analisis."],
                "llm_analysis": "Esperando configuracion de tu portafolio."
            }

        ticker = state.ticker or "SPY"

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

        greeks_str = (
            f"Delta={round(net_delta,2)}, Gamma={round(net_gamma,2)}, "
            f"Theta={round(net_theta,2)}, Vega={round(net_vega,2)}"
        )

        # Obtener contexto de mercado
        market_context_str = "Contexto no disponible"
        if state.market_context:
            market_context_str = await AIAnalyzerService._format_market_context(state.market_context)

        # Compilar reporte de patas
        legs_summary = ""
        for i, leg in enumerate(legs):
            action_es = "Comprado" if leg.action == "buy" else "Vendido"
            if leg.type == "call":
                tipo_es = "Call"
            elif leg.type == "put":
                tipo_es = "Put"
            else:
                tipo_es = "Acciones (Stock)"
            
            legs_summary += f"Pata {i+1}: {action_es} {leg.qty} {tipo_es} Precio/Strike ${leg.strike} Exp:{leg.expiration} (Vol:{leg.volume} OI:{leg.open_interest})\n"

        # UNA sola llamada al LLM con todo el contexto pre-armado
        llm_response = await AIAnalyzerService._call_llm(ticker, greeks_str, market_context_str, legs_summary)

        return {
            "risk_score": risk,
            "net_greeks": {
                "delta": round(net_delta, 2),
                "gamma": round(net_gamma, 2),
                "theta": round(net_theta, 2),
                "vega": round(net_vega, 2)
            },
            "quick_tips": tips if tips else ["Posicion neutral. Las griegas estan estabilizadas."],
            "llm_analysis": llm_response
        }
