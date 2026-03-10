# OptionStrat AI – Advanced Derivatives Simulator

[English](README.md) | [Español](README-es.md) | [Português](README-pt.md) | [中文](README-zh.md)

**OptionStrat AI** is a software and financial engineering platform specialized in the predictive simulation of derivatives (American-style Stock Options) driven by Artificial Intelligence and quantitative mathematics.

Designed for retail, institutional, and professional investors interested in the world of stock options, this tool transcends typical P&L calculators. It merges **Black-Scholes-Merton**, **Financial News** (Finviz), **Insider Trading Movements** operating in the shadows (13F filings via YahooQuery), and an interactive **LLM agent** to interpret the net risk of the portfolio. Everything is packaged under a state-of-the-art asynchronous modern React Front-End.

---

## ▶️ Demo and Platform in Action
*Complete showcase of the platform, ideal for introducing the technology to new users and interested parties.*

![OptionStrat AI Demo](assets/video_muestra.gif)

---

## 📸 Key Features

1. **Option Builder (Enriched T-Quote)**
   - Extracts real option chains via *Yahoo Finance* (Live Bid, Ask, Strikes, IV, Volume, and Open Interest).
   - 1:1 symmetry, allows building and inserting positions of underlying Stocks vs. Derivative Options for complex hedging strategies *(Covered Calls, Protective Puts)*.

2. **Dynamic Risk Heatmap (Python Quant Engine)**
   - BSM engine operating in milliseconds that processes changes in price (X Axis) versus days to expiration (Y Axis) to project the combined net PnL of your entire inventory.
   - Features reactive sliders for *Volatility Shock (Vega)* and accelerated forward simulation.

3. **Artificial Intelligence (Contextual LLM)**
   - You no longer interpret the Greeks "blindly". An AI Quantitative Analyst (via structured OpenAI) will read the entire portfolio, aggregating Theta Decay and Net Vega Risk, warning you if your Delta becomes asymmetric or if you have blind gamma. Additionally, it reads market sentiment, recent insider activity, analyst ratings, and the average analyst target price.

4. **Institutional Sentiment Filter**
   - Before analysis, the back-end extracts news from **FinViz**, interpreting them with *VaderSentiment* under neutral, bearish, or bullish metrics.
   - Cross-references this data with **Insider Trading** volume, identifying C-Levels diluting positions or accumulating strong stakes in their own company over the past week.

5. **Cyclical Mathematical Optimizer (Theta Gang Recommender)**
   - Requests strategies according to a volatility profile: Conservative (~85% Probability of Profit), Balanced, or Aggressive.
   - Automatically filters out *zombie* options by scanning strict real liquidity requirements (Volume > 10, Open Interest > 50).
   - Designs Bull Put Spreads, Symmetrical Iron Condors, or Strangles ready to click *"Load into Simulator"*.

---

## 🛠 Technological Architecture (Stack)

### Backend (Data, Quant & AI Engine)
- **FastAPI**: Asynchronous routing for maximum streaming speed of greeks and P&L arrays.
- **Pydantic**: Strong typing for business models (OptionLeg, StrategyState).
- **Pandas & NumPy**: Tensor processing to clean Option Chains and underlying matrices.
- **SciPy**: Native statistical distributions (PDF, CDF) for Black-Scholes formulation of the Greeks (Delta, Gamma, Vega, Theta, Rho).
- **YFinance & YahooQuery**: Fault-tolerant main web-scraping engines for spot price gathering and 13F.
- **VaderSentiment & BeautifulSoup4**: Raw native Natural Language Processing over web HTML feeds to categorize Euphoria/Panic.
- **LiteLLM**: Hybrid LLM Router (To orchestrate requests to OpenAI / OpenRouter into structured variables).

### Frontend (Client-Side)
- **React.js 18**: Fast VDOM.
- **Vite**: Ultra Fast Bundler with hot-reload.
- **Zustand**: Global state management to prevent un-necessary re-renders, tightly coupling the interactive Builder chain and Heatmap in perfect asynchronous synchrony (Debouncing functions included).
- **Recharts**: Reactive graphic rendering for two-dimensional P&L risk maps.
- **Glassmorphism CSS3**: "Dark Institutional" theme 100% vectorized in vanilla CSS. No Tailwind for greater purism and consistency.

---

## 🚀 Local Installation

To run OptionStrat AI and avoid CORS issues, you need to run the Back-End and Front-End on separate ports concurrently.

### 1. Launch the Backend Server
```bash
# Navigate to the backend folder
cd backend

# Create your Virtual Environment and install it (Windows)
python -m venv venv
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
# (The requirements include: fastapi, uvicorn, pydantic, pandas, numpy, scipy, yfinance, yahooquery, litellm, vaderSentiment, beautifulsoup4, fake_useragent, etc.)

# [IMPORTANT] You need to set environment variables (e.g., OpenAI API if you want to use AI Insights).
# Edit your .env: OPENAI_API_KEY=your_key_here

# Launch the server on port 8000
uvicorn app.main:app --reload
```

### 2. Launch the Frontend Client
```bash
# Open a new terminal
# Navigate to the frontend folder
cd frontend

# Install dependencies (Node Modules)
npm install

# Run the Frontend server on localhost (Points locally via Client Proxy Axios to 8000)
npm run dev
```

### 3. Run!
Open your browser at `http://localhost:5173` or the port Vite assigns and start exploring by adding institutional tickers like AAPL, SPY, or TSLA.

---

## 📝 Future Roadmap

- Integration of Binomial, Dynamic Trinomial Trees, and Monte Carlo for better early approximation of early dividend assignment in US options.
- User histories in PostgreSQL DB with Risk-Reward ratio profiles and Monte-Carlo simulations superimposed on a 3D grid.
- Future connection to broker APIs for order execution (IBKR, Alpaca, etc).

> Programmed and orchestrated with passion by EconomiaUNMSM.
