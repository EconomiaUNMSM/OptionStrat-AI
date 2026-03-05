# OptionStrat AI – Advanced Derivatives Simulator

**OptionStrat AI** es una plataforma de software e ingeniería financiera especializada en la simulación predictiva de derivados (Opciones sobre Acciones con estilo Americano) impulsada por Inteligencia Artificial y matemáticas cuantitativas.

Diseñada para inversionistas minoristas, institucionales y profesionales interesados en el mundo de las opciones sobre acciones, esta herramienta trasciende las típicas calculadoras de P&L, fusionando **Black-Scholes-Merton**, **Noticias Financieras** (Finviz), **Movimientos de Insiders** operando en las sombras (13F filings mediante YahooQuery) y agente de **LLM interactivo** para interpretar el riesgo neto del portafolio. Todo, empaquetado bajo un Front-End React de última generación asíncrono.

---

## ▶️ Demo y Plataforma en Acción
*Muestra completa de la plataforma ideal para introducir la tecnología a nuevos usuarios e interesados.*

<video width="100%" controls>
  <source src="https://github.com/EconomiaUNMSM/OptionStrat-AI/raw/main/assets/video_muestra.mp4" type="video/mp4">
  Tu navegador no soporta la etiqueta de video.
</video>

---

## 📸 Funcionalidades Clave

1. **Option Builder (T-Quote Enriquecido)**
   - Extrae cadenas reales de opciones via *Yahoo Finance* (Bid, Ask, Strikes, IV, Volume y Open Interest vivo).
   - Simetría 1:1, permite construir e insertar posiciones de Acciones de Contado frente a Opciones Derivadas para estrategias complejas de cobertura *(Covered Calls, Protective Puts)*.

2. **Heatmap Dinámico de Riesgos (Python Quant Engine)**
   - Motor BSM en milisegundos que procesa cambios en precio (Eje X) frente a los días que faltan hacia la expiración (Eje Y) para proyectar el PnL neto combinado de todo tu inventario.
   - Cuenta con sliders reactivos para *Shock de Volatilidad (Vega)* y simulación acelerada hacia adelante.

3. **Inteligencia Artificial (LLM Contextual)**
   - Ya no interpretas las Griegas "a ciegas". Un Analista Cuantitativo de IA (vía OpenAI estructurado) leerá la cartera completa, agregando el Theta Decay y el Vega Net Risk, avisándote si tu Delta se vuelve asimétrico o tienes gamma ciego. Además, leerá el sentimiento del mercado, los insiders más recientes, los analistas y el precio objetivo promedio de los analistas.

4. **Filtro Institucional de Sentimiento**
   - Antes del análisis, el back-end extrae noticias de **FinViz** interpretándolas con *VaderSentiment* bajo métricas neutrales, bajistas o alcistas.
   - Cruza estos datos con el volumen del **Insider Trading**, identificando C-Levels que están diluyendo posiciones o acumulando participaciones fuertes en su propia empresa la última semana.

5. **Optimizador Matemático Cíclico (Theta Gang Recommender)**
   - Pide estrategias según perfil de volatilidad: Conservador (~85% Probability of Profit), Balanceado o Agresivo.
   - Automáticamente filtra opciones *zombies* escaneando exigencias de liquidez estrictas reales (Volume > 10, Open Interest > 50).
   - Diseña Bull Put Spreads, Iron Condors Simétricos o Strangles listos para apretar *"Cargar al Simulador"*.

---

## 🛠 Arquitectura Tecnológica (Stack)

### Backend (Data, Quant & AI Engine)
- **FastAPI**: Enrutamiento asíncrono para velocidad máxima de streaming de greeks y arrays P&L.
- **Pydantic**: Tipado fuerte de modelos de negocio (OptionLeg, StrategyState).
- **Pandas & NumPy**: Procesamiento tensorial para limpiar Option Chains y matrices subyacentes.
- **SciPy**: Distribuciones estadísticas nativas (PDF, CDF) para formulación Black-Scholes de las Griegas (Delta, Gamma, Vega, Theta, Rho).
- **YFinance & YahooQuery**: Motores principales de web-scraping tolerantes a fallos para recolección de precios spots y 13F.
- **VaderSentiment & BeautifulSoup4**: Natural Language Processing nativo crudo sobre feeds HTML web para categorizar Euphoria/Pánico.
- **LiteLLM**: Router híbrido LLM (Para orquestar envíos a OpenAI / OpenRouter en variables estructuradas).

### Frontend (Client-Side)
- **React.js 18**: VDOM veloz.
- **Vite**: Ultra Fast Bundler en hot-reload.
- **Zustand**: Gestión global de estado anti un-necessary re-renders para acoplar la cadena interactiva del Builder y Heatmap en perfecta sincronía asíncrona (Debouncing functions incluídas).
- **Recharts**: Rendering gráfico reactivo para mapas de riesgos bidimensionales de P&L.
- **Glassmorphism CSS3**: Temática "Dark Institutional" 100% vectorizada en CSS vanilla. Sin Tailwind para mayor purismo y consistencia.

---

## 🚀 Instalación Local 

Para correr OptionStrat AI y evitar CORS requieres correr Back-End y Front-End en puertos separados concurrentemente.

### 1. Levantar el Backend Server
```bash
# Navega a la carpeta backend
cd backend

# Crea tu entorno Virtual e instalalo (Windows)
python -m venv venv
venv\Scripts\activate

# Instala todas las dependencias
pip install -r requirements.txt
# (El requirements incluye: fastapi, uvicorn, pydantic, pandas, numpy, scipy, yfinance, yahooquery, litellm, vaderSentiment, beautifulsoup4, fake_useragent, etc)

# [IMPORTANTE] Necesitas setear variables de entorno (Ej: API de OpenAI si deseas usar Ai Insights). 
# Edita tu .env: OPENAI_API_KEY=tu_clave_aqui

# Lanza el servidor en el puerto 8000
uvicorn app.main:app --reload
```

### 2. Levantar el Frontend Client
```bash
# Abre una nueva terminal
# Navega a la carpeta frontend
cd frontend

# Instala dependencias (Node Modules)
npm install

# Corre el servidor Frontend en localhost (Apunta localmente vía Client Proxy Axios al 8000)
npm run dev
```

### 3. ¡Ejecutar!
Abre tu navegador en `http://localhost:5173` o el puerto que asigne Vite y comienza a explorar agregando Tickers institucionales como AAPL, SPY, o TSLA.

---

## 📝 Roadmap a Futuro

- Integración de Árboles Binomiales, Trinomiales Dinámicos y Monte Carlo para mejor aproximación anticipada de asignación de dividendos tempranos en opciones USA.
- Historiales de usuario en DB PostgreSQL con perfiles de Risk-Reward ratios y simulaciones Mote-Carlo superpuestas a un grid 3D.
- Conexión ulterior a APIs de brokers para ejecución de órdenes (IBKR, Alpaca, etc).

> Programado y orquestado con pasión por EconomiaUNMSM.
