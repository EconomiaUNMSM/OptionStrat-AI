import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OptionStrat API",
    description="Backend para el simulador inteligente de opciones financieras",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Must be specific in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routers import option_chains, calculations, ai_insights, recommender, market

app.include_router(option_chains.router, prefix="/api")
app.include_router(calculations.router, prefix="/api")
app.include_router(ai_insights.router, prefix="/api")
app.include_router(recommender.router, prefix="/api")
app.include_router(market.router, prefix="/api")

@app.get("/")
def root_status():
    return {"status": "ok", "message": "OptionStrat Backend is running."}
