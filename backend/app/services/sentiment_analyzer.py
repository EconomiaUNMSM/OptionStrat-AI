import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import asyncio

# The user requested to use fake_useragent, vaderSentiment, html5lib, beautifulsoup4
try:
    from fake_useragent import UserAgent
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    logging.warning("Missing dependencies for sentiment analysis. Please install fake_useragent and vaderSentiment")

class SentimentAnalyzer:
    @staticmethod
    async def get_recent_sentiment(ticker: str, days: int = 5) -> dict:
        """
        Scrapes Finviz for recent news of a ticker, calculates Vader sentiment,
        and returns the average sentiment over the last N days.
        """
        url = "https://finviz.com/quote.ashx?t={}&p=d"
        extracciones = []
        
        try:
            # We use an async wrapper to not block the main fastAPI thread
            loop = asyncio.get_event_loop()
            
            def fetch_and_parse():
                ua = UserAgent()
                header = {"User-Agent": str(ua.chrome)}
                r = requests.get(url=url.format(ticker), headers=header, timeout=10)
                soup = BeautifulSoup(r.content, "html5lib")
                
                tabla_noticias = soup.find(id="news-table")
                if not tabla_noticias:
                    return []
                    
                noticias = tabla_noticias.findAll(name="tr")
                data = []
                
                for noticia in noticias:
                    a_tag = noticia.find(name="a", attrs={"class": "tab-link-news"})
                    if not a_tag:
                        continue
                        
                    titular = a_tag.text
                    td_tag = noticia.find(name="td")
                    if not td_tag:
                        continue
                        
                    fecha_publicacion = td_tag.text.replace("\n", "").strip().split()
                    
                    if len(fecha_publicacion) == 2:
                        fecha = fecha_publicacion[0]
                        hora = fecha_publicacion[1]
                        if fecha.lower() == "today":
                            fecha = datetime.now().strftime("%b-%d-%y")
                    else:
                        hora = fecha_publicacion[0]
                        # Inherit the date from the last processed item if only time is provided (Finviz format)
                        fecha = data[-1][1] if data else datetime.now().strftime("%b-%d-%y")
                        
                    data.append([ticker, fecha, hora, titular])
                return data

            extracciones = await loop.run_in_executor(None, fetch_and_parse)
            
            if not extracciones:
                return {"score": 0.0, "news_count": 0, "status": "no_news"}
                
            noticias_df = pd.DataFrame(data=extracciones, columns=["Ticker", "Fecha", "Hora", "Titulares"])
            noticias_df["Fecha"] = pd.to_datetime(noticias_df["Fecha"], format="%b-%d-%y", errors='coerce')
            noticias_df = noticias_df.dropna(subset=['Fecha'])
            
            sia = SentimentIntensityAnalyzer()
            noticias_df["Sentimiento"] = noticias_df["Titulares"].apply(lambda x: sia.polarity_scores(x)["compound"])
            
            # Group by Date and mean
            noticias_agrupadas = noticias_df[["Ticker", "Fecha", "Sentimiento"]].groupby(["Ticker", "Fecha"]).mean()
            noticias_agrupadas.reset_index(inplace=True)
            
            # Filter last 5 days
            fecha_1 = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            fechas_especificas = [fecha_1 - timedelta(days=i) for i in range(days)]
            
            noticias_filtradas = noticias_agrupadas[noticias_agrupadas["Fecha"].isin(fechas_especificas)]
            
            # Calculate total average
            avg_sentiment = noticias_filtradas["Sentimiento"].mean()
            if pd.isna(avg_sentiment):
                avg_sentiment = noticias_df["Sentimiento"].mean() # Fallback to all extracted if no recent dates match perfectly
                if pd.isna(avg_sentiment):
                    avg_sentiment = 0.0
            
            recent_headlines = noticias_df["Titulares"].head(5).tolist()
            
            return {
                "score": float(avg_sentiment),
                "news_count": len(noticias_df),
                "recent_headlines": recent_headlines,
                "status": "success"
            }
            
        except Exception as e:
            logging.error(f"Sentiment Analysis Error for {ticker}: {str(e)}")
            return {"score": 0.0, "news_count": 0, "status": "error", "message": str(e)}
