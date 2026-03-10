# OptionStrat AI – Advanced Derivatives Simulator (高级衍生品模拟器)

[English](README.md) | [Español](README-es.md) | [Português](README-pt.md) | [中文](README-zh.md)

**OptionStrat AI** 是一款软件和金融工程平台，专门用于衍生品（美式股票期权）的预测性模拟，由人工智能和定量数学驱动。

专为对股票期权世界感兴趣的零售、机构和专业投资者而设计，该工具超越了典型的盈亏（P&L）计算器，融合了 **布莱克-斯科尔斯-默顿 (Black-Scholes-Merton)** 模型、**财经新闻** (Finviz)、暗中操作的 **内幕交易动态**（通过 YahooQuery 获取 13F 文件）以及**交互式大语言模型 (LLM) 代理**来解释投资组合的净风险。所有的功能都被打包在最新的异步现代化 React 前端下。

---

## ▶️ 演示与平台实况
*该平台的完整展示，非常适合向新用户和有关方面介绍这项技术。*

![OptionStrat AI 演示](assets/video_muestra.gif)

---

## 📸 核心功能

1. **期权构建器（丰富的 T 型报价）**
   - 通过 *Yahoo Finance* 提取真实的期权链（实时买价、卖价、行权价、隐含波动率 (IV)、成交量 和 未平仓合约）。
   - 1:1 对称，允许针对底层股票和衍生期权结合构建头寸，以实现复杂的对冲策略（例如：*备兑看涨期权 (Covered Calls)*、*保护性看跌期权 (Protective Puts)*）。

2. **动态风险热力图（Python 宽客引擎）**
   - 毫秒级的 BSM 引擎处理价格变化（X 轴）与距离到期日剩余天数（Y 轴）之间的关系，以预测您整个库存的总结合净盈亏 (PnL)。
   - 提供反应式滑块以用于*波动率冲击 (Vega)*及加速远期模拟。

3. **人工智能（上下文 LLM）**
   - 您再也不需要“盲目”地解读希腊字母了。人工智能量化分析师（通过结构化 OpenAI）将读取整个投资组合，汇总 Theta 衰减和 Vega 净风险，如果您的 Delta 变得不对称或者您有盲目的 Gamma，它会及时提醒您。此外，它还会读取市场情绪、最新的内幕交易、分析师评级和分析师平均目标价格。

4. **机构情绪过滤器**
   - 在分析之前，后端会从 **FinViz** 提取新闻，通过 *VaderSentiment* 以中立、看跌或看涨的标准进行解读。
   - 将此数据与**内幕交易**成交量交叉比对，识别在过去一周内稀释头寸或是增持本公司股份的高管 (C-Levels)。

5. **系统化数学优化器（Theta 帮推荐器）**
   - 根据波动率偏好请求策略：保守（约 85%的胜率）、平衡或激进。
   - 通过扫描严格的真实流动性要求（成交量 > 10，未平仓合约 > 50），自动过滤“僵尸”期权。
   - 设计看涨期权价差 (Bull Put Spreads)、对称的铁鹰组合 (Iron Condors) 或宽跨式组合 (Strangles)，随时可点击*“加载至模拟器”*。

---

## 🛠 技术架构 (Stack)

### 后端 (Data, Quant & AI Engine)
- **FastAPI**：异步路由设计，可为希腊字母流和 P&L 矩阵提供最高速度。
- **Pydantic**：业务模型强类型（期权腿 OptionLeg, 策略状态 StrategyState）。
- **Pandas & NumPy**：张量处理，清理期权链及底层矩阵。
- **SciPy**：应用原生统计分布 (PDF, CDF) 实现希腊字母的 Black-Scholes 公式计算（Delta、Gamma、Vega、Theta、Rho）。
- **YFinance & YahooQuery**：主要容错网页抓取引擎，拉取现货价格和 13F 报表。
- **VaderSentiment & BeautifulSoup4**：直接在 Web HTML Feed 上运用原生自然语言处理算法对狂热/恐慌情绪进行分类。
- **LiteLLM**：混合 LLM 路由器（能够将向 OpenAI / OpenRouter 发送的请求编排成结构化变量）。

### 前端 (Client-Side)
- **React.js 18**：快速虚拟 DOM (VDOM)。
- **Vite**：超高速热重载打包器。
- **Zustand**：全局状态管理，防除多余渲染，将交互式构建器链和热力图在完美的异步同步中紧密结合（包含防抖 Debencing 函数）。
- **Recharts**：反映式图表渲染引擎用于二维 P&L 风险映射图。
- **Glassmorphism CSS3**：100%原生的 Vanilla CSS，带来“暗色机构”矢量化高大上主题。无 Tailwind 以坚持更高的纯粹与一致性。

---

## 🚀 本地安装运行

为运行 OptionStrat AI 并避免 CORS 跨域问题，您需要在分离的端口上并发部署后端和前端。

### 1. 启动后端服务器
```bash
# 导航至后端文件夹
cd backend

# 创建并激活您的虚拟环境 (Windows系统使用如下命令)
python -m venv venv
venv\Scripts\activate

# 安装所有依赖
pip install -r requirements.txt
# (依赖列表包括：fastapi, uvicorn, pydantic, pandas, numpy, scipy, yfinance, yahooquery, litellm, vaderSentiment, beautifulsoup4, fake_useragent 等)

# [重要] 如果希望进行 AI 深度分析，需要设置环境变量 (例如：OpenAI API 密钥)
# 编辑您的 .env 文件: OPENAI_API_KEY=your_key_here

# 启动服务端配置在 8000 端口
uvicorn app.main:app --reload
```

### 2. 启动前端客户端
```bash
# 打开一个新终端
# 导航至前端文件夹
cd frontend

# 安装依赖模块 (Node Modules)
npm install

# 在 localhost 上运行前端服务端 (通过 Client Proxy Axios 指向 localhost:8000)
npm run dev
```

### 3. 开始执行！
在浏览器中打开 `http://localhost:5173` 或 Vite 指定的其他端口，在里面添加苹果 (AAPL)、标普 (SPY) 或特斯拉 (TSLA) 等机构代码开始探索。

---

## 📝 未来开发路线图

- 集成二项式、动态三项式树和蒙特卡洛模型，以更好的预测美式期权提早除息的情景。
- 采用 PostgreSQL 数据库存储用户历史数据，并包括叠加于 3D 矩阵的风险回报(Risk-Reward)画像及其蒙特卡洛模拟。
- 以后进一步开发连接至券商的 API 实现订单执行 (IBKR, Alpaca 等)。

> 怀着十足热忱由 EconomiaUNMSM 协同编程与策划。
