# OptionStrat AI – Simulador Avançado de Derivativos

[English](README.md) | [Español](README-es.md) | [Português](README-pt.md) | [中文](README-zh.md)

**OptionStrat AI** é uma plataforma de software e engenharia financeira especializada na simulação preditiva de derivativos (Opções de Ações de Estilo Americano) impulsionada por Inteligência Artificial e matemática quantitativa.

Projetada para investidores de varejo, institucionais e profissionais interessados no mundo das opções de ações, esta ferramenta transcende calculadoras típicas de P&L, mesclando **Black-Scholes-Merton**, **Notícias Financeiras** (Finviz), **Movimentação de Insiders** operando nas sombras (arquivos 13F via YahooQuery) e o agente interativo de **LLM** para interpretar o risco líquido do portfólio. Tudo embalado sob um Front-End React de última geração assíncrono.

---

## ▶️ Demo e Plataforma em Ação
*Mostra completa da plataforma, ideal para apresentar a tecnologia a novos usuários e interessados.*

![Demonstração OptionStrat AI](assets/video_muestra.gif)

---

## 📸 Principais Funcionalidades

1. **Option Builder (T-Quote Enriquecido)**
   - Extrai cadeias reais de opções via *Yahoo Finance* (Bid, Ask, Strikes, IV, Volume e Open Interest ao vivo).
   - Simetria 1:1, permite construir e inserir posições de Ações subjacentes contra Opções Derivadas para estratégias complexas de hedge *(Covered Calls, Protective Puts)*.

2. **Heatmap Dinâmico de Riscos (Python Quant Engine)**
   - Motor BSM em milissegundos que processa mudanças no preço (Eixo X) contra os dias restantes para o vencimento (Eixo Y) para projetar o PnL líquido combinado do seu inventário inteiro.
   - Possui sliders reativos para *Choque de Volatilidade (Vega)* e simulação avançada acelerada.

3. **Inteligência Artificial (LLM Contextual)**
   - Você não interpreta mais as Gregas "às cegas". Um Analista Quantitativo de IA (via OpenAI estruturado) lerá o portfólio completo, agregando o Theta Decay e o Vega Net Risk, avisando se seu Delta se tornar assimétrico ou se você tiver gama cego. Além disso, lerá o sentimento do mercado, os insiders mais recentes, os analistas e o preço-alvo médio dos analistas.

4. **Filtro Institucional de Sentimento**
   - Antes da análise, o back-end extrai notícias da **FinViz**, interpretando-as com *VaderSentiment* sob métricas neutras, de baixa ou de alta.
   - Põe em referência cruzada esses dados com o volume do **Insider Trading**, identificando C-Levels que estão diluindo posições ou acumulando forte controle em sua própria empresa na última semana.

5. **Otimizador Matemático Cíclico (Theta Gang Recommender)**
   - Solicita estratégias de acordo com o perfil de volatilidade: Conservador (~85% de Probabilidade de Lucro), Equilibrado ou Agressivo.
   - Filtra automaticamente opções *zumbis*, escaneando exigências reais de liquidez estritas (Volume > 10, Open Interest > 50).
   - Desenha Bull Put Spreads, Iron Condors Simétricos ou Strangles prontos para clicar em *"Carregar no Simulador"*.

---

## 🛠 Arquitetura Tecnológica (Stack)

### Backend (Data, Quant & AI Engine)
- **FastAPI**: Roteamento assíncrono para velocidade máxima de streaming das gregas e arrays P&L.
- **Pydantic**: Tipagem forte de modelos de negócios (OptionLeg, StrategyState).
- **Pandas & NumPy**: Processamento tensorial para limpar Cadeias de Opções e matrizes subjacentes.
- **SciPy**: Distribuições estatísticas nativas (PDF, CDF) para formulação Black-Scholes das Gregas (Delta, Gamma, Vega, Theta, Rho).
- **YFinance & YahooQuery**: Motores principais de web-scraping tolerantes a falhas para coleta de preços spot e 13F.
- **VaderSentiment & BeautifulSoup4**: Processamento de Linguagem Natural puro nativo sobre feeds HTML da web para categorizar Euforia/Pânico.
- **LiteLLM**: Roteador Híbrido LLM (Para orquestrar envios para OpenAI / OpenRouter em variáveis estruturadas).

### Frontend (Client-Side)
- **React.js 18**: VDOM veloz.
- **Vite**: Ultra Fast Bundler com hot-reload.
- **Zustand**: Gestão de estado global anti-renderizações desnecessárias, combinando a cadeia interativa do Builder e o Heatmap em perfeita sincronia assíncrona (funções Debouncing incluídas).
- **Recharts**: Renderização gráfica reativa para mapas de risco bidimensionais de P&L.
- **Glassmorphism CSS3**: Tema "Dark Institutional" 100% vetorizado em CSS vanilla. Sem Tailwind para maior purismo e consistência.

---

## 🚀 Instalação Local

Para rodar o OptionStrat AI e evitar o CORS, você precisa rodar o Back-End e Front-End em portas separadas concorrentemente.

### 1. Iniciar o Servidor Backend
```bash
# Navegue até a pasta backend
cd backend

# Crie seu ambiente virtual e instale-o (Windows)
python -m venv venv
venv\Scripts\activate

# Instale todas as dependências
pip install -r requirements.txt
# (O requirements inclui: fastapi, uvicorn, pydantic, pandas, numpy, scipy, yfinance, yahooquery, litellm, vaderSentiment, beautifulsoup4, fake_useragent, etc)

# [IMPORTANTE] Você precisa definir as variáveis de ambiente (Ex: API da OpenAI se você deseja usar Ai Insights).
# Edite seu .env: OPENAI_API_KEY=sua_chave_aqui

# Inicie o servidor na porta 8000
uvicorn app.main:app --reload
```

### 2. Iniciar o Cliente Frontend
```bash
# Abra um novo terminal
# Navegue até a pasta frontend
cd frontend

# Instale as dependências (Node Modules)
npm install

# Inicie o servidor Frontend em localhost (Aponta localmente via Client Proxy Axios para a porta 8000)
npm run dev
```

### 3. Executar!
Abra seu navegador em `http://localhost:5173` ou na porta que o Vite atribuiu e comece a explorar adicionando Tickers institucionais como AAPL, SPY ou TSLA.

---

## 📝 Roteiro Futuro

- Integração de Árvores Binomiais, Trinomiais Dinâmicas e Monte Carlo para uma melhor aproximação inicial de atribuição antecipada de dividendos em opções dos EUA.
- Históricos de usuários em BD PostgreSQL com perfis de relação Risco-Recompensa e simulações de Monte-Carlo sobrepostas a uma grade 3D.
- Futura conexão com APIs de corretoras para execução de ordens (IBKR, Alpaca, etc).

> Programado e orquestrado com paixão pela EconomiaUNMSM.
