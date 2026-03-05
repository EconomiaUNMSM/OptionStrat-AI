from fastapi import APIRouter
from app.schemas.strategy_models import StrategyState, HeatmapResponse
from app.services.strategy_builder import StrategyBuilder

router = APIRouter(
    prefix="/calculations",
    tags=["Model Calculations"]
)

@router.post("/heatmap", response_model=HeatmapResponse)
async def generate_advanced_heatmap(state: StrategyState):
    """
    Ruta PRINCIPAL (Estrella) de OptionStrat.
    Recibe un estado base (la estrategia del usuario en React).
    Genera un grid numérico 2D cruzando iteraciones de tiempo y de precio subyacente consumiendo Black Scholes.
    """
    try:
        # Calcular el heatmap grid consumiendo el StrategyBuilder
        result = StrategyBuilder.generate_heatmap_grid(state)
        
        return {
            "status": "success",
            "max_profit": result["max_profit"],
            "max_loss": result["max_loss"],
            "heatmap_grid": result["heatmap_grid"]
        }
    except Exception as e:
        import logging
        logging.error(f"Error calculating Heatmap: {e}")
        return {
            "status": "error",
            "heatmap_grid": []
        }

