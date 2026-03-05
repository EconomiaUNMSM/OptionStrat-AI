from fastapi import APIRouter, HTTPException
import yfinance as yf
from yahooquery import Ticker as YQTicker
from app.services.sentiment_analyzer import SentimentAnalyzer
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()

class MarketContextResponse(BaseModel):
    symbol: str
    current_price: float
    # Sentiment
    sentiment_score: float
    sentiment_status: str
    recent_news: List[str]
    # Analyst Targets
    target_mean: Optional[float]
    target_median: Optional[float]
    recommendation_key: Optional[str]
    # Details & Metrics
    long_business_summary: Optional[str]
    forward_pe: Optional[float]
    trailing_pe: Optional[float]
    debt_to_equity: Optional[float]
    # Insiders
    insider_purchases: Optional[int]
    insider_sales: Optional[int]
    top_insiders: List[Dict[str, Any]]

@router.get("/market-context/{symbol}", response_model=MarketContextResponse)
async def get_market_context(symbol: str):
    """
    Combines YFinance, YahooQuery (Insiders) and Finviz/Vader Sentiment.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # YahooQuery para insiders
        yq_ticker = YQTicker(symbol)
        
        # Determine actual price
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if not price:
            raise HTTPException(status_code=404, detail=f"No se pudo obtener el precio de {symbol}")

        # Sentiment Analysis
        sentiment_data = await SentimentAnalyzer.get_recent_sentiment(symbol)
        # Manejo de Insiders con YahooQuery
        insider_purchases = 0
        insider_sales = 0
        top_insiders = []
        
        try:
            holders_breakdown = yq_ticker.major_holders or {}
        except Exception:
            holders_breakdown = {}
            
        try:
            ins_trans = yq_ticker.insider_transactions
            if hasattr(ins_trans, "empty") and not ins_trans.empty:
                import pandas as pd
                if isinstance(ins_trans, pd.DataFrame):
                    if "transactionText" in ins_trans.columns:
                        ins_trans['text_lower'] = ins_trans['transactionText'].astype(str).str.lower()
                        purchases_df = ins_trans[ins_trans['text_lower'].str.contains('purchase')]
                        sales_df = ins_trans[ins_trans['text_lower'].str.contains('sale')]
                        
                        insider_purchases = len(purchases_df)
                        insider_sales = len(sales_df)
                        
                        last_3 = ins_trans.head(3)
                        for _, row in last_3.iterrows():
                            val_shares = row.get('shares', 0)
                            safe_name = row.get('filerName', 'Unknown')
                            safe_relation = row.get('filerRelation', 'Insider')
                            tt_low = str(row.get('transactionText', '')).lower()
                            
                            sign = -1 if 'sale' in tt_low else 1

                            if pd.isna(val_shares): val_shares = 0
                            if pd.isna(safe_name): safe_name = 'Unknown'
                            
                            top_insiders.append({
                                "name": str(safe_name),
                                "position": str(safe_relation),
                                "shares_traded": int(val_shares) * sign
                            })
        except Exception as e:
            print(f"Error procesando insiders YQ para {symbol}:", e)
        
        return MarketContextResponse(
            symbol=symbol.upper(),
            current_price=price,
            sentiment_score=sentiment_data.get("score", 0.0),
            sentiment_status=sentiment_data.get("status", "unknown"),
            recent_news=sentiment_data.get("recent_headlines", []),
            target_mean=info.get("targetMeanPrice"),
            target_median=info.get("targetMedianPrice"),
            recommendation_key=info.get("recommendationKey"),
            long_business_summary=info.get("longBusinessSummary", "")[:300] + "..." if info.get("longBusinessSummary") else "",
            forward_pe=info.get("forwardPE"),
            trailing_pe=info.get("trailingPE"),
            debt_to_equity=info.get("debtToEquity"),
            insider_purchases=insider_purchases or info.get("insiderPurchases", 0),
            insider_sales=insider_sales or info.get("insiderSales", 0),
            top_insiders=top_insiders
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
