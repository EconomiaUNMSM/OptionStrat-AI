from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

# Modelo para cada "pata" de la estrategia (Leg)
class OptionLeg(BaseModel):
    type: str = Field(..., pattern="^(call|put|stock)$", description="Tipo de activo: call, put o stock")
    action: str = Field(..., pattern="^(buy|sell)$", description="Acción a realizar: buy o sell")
    strike: float = Field(..., gt=0, description="Precio de ejercicio (Strike)")
    expiration: date = Field(..., description="Fecha de expiración (YYYY-MM-DD)")
    qty: int = Field(..., gt=0, description="Cantidad de contratos (1 equivale a 100 acciones)")
    premium: float = Field(default=0.0, ge=0.0, description="Prima pagada o recibida por el contrato")
    volume: Optional[int] = Field(default=0, description="Volumen del contrato")
    open_interest: Optional[int] = Field(default=0, description="Interés abierto del contrato")

# Modelo Principal para el Frontend cuando pida un Heatmap o cálculo
class StrategyState(BaseModel):
    underlying_price: float = Field(..., gt=0, description="Precio actual (o simulado) del activo subyacente")
    volatility_shock: float = Field(default=0.0, description="Shock de VIX/Volatilidad a simular (ej: 0.05 para +5%)")
    days_to_simulate: int = Field(default=30, ge=1, le=365, description="Dias hacia adelante para el heatmap")
    legs: List[OptionLeg] = Field(..., min_length=1, description="Lista de posiciones en opciones (min 1 pata)")
    ticker: Optional[str] = Field(default=None, description="Símbolo del activo subyacente (ej: AAPL)")
    market_context: Optional[dict] = Field(default=None, description="Pre-fetched Yfinance and Sentiment info")    
# Modelo de Salida para el Heatmap (Respuesta de la API)
class HeatmapResponse(BaseModel):
    status: str
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    # Esta variable en el futuro será una matriz/grid para React.
    heatmap_grid: list = Field(default_factory=list, description="Lista 2D o diccionarios con el grid P&L calculado")
