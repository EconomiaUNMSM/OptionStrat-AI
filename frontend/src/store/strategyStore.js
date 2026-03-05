import { create } from 'zustand';
import api from '../api/client';

let _calcTimeout = null;
let _calcVersion = 0; // Lock anti-concurrencia

export const useStrategyStore = create((set, get) => ({
    // Estado Global
    ticker: '',
    spotPrice: 0,
    riskFreeRate: 0.05,

    // Expiraciones disponibles (lista completa de fechas string)
    allExpirations: [],
    selectedExpiration: '',

    // Cadena de opciones para la expiración seleccionada
    optionChain: { calls: [], puts: [] },

    // Loading states
    isLoadingChain: false,
    isLoadingExpiration: false,
    isLoadingMarketContext: false,

    // Parámetros Interactivos del Heatmap
    volatilityShock: 0,
    daysToSimulate: 30,

    // Posiciones armadas por el usuario
    legs: [],

    // Resultados del Backend
    heatmapData: [],
    aiInsights: null,
    marketContext: null,
    isLoadingHeatmap: false,

    // --- Acciones ---

    // 1. Paso 1: Cargar expiraciones + spot price (rápido)
    fetchExpirations: async (sym) => {
        set({
            isLoadingChain: true,
            legs: [],
            heatmapData: [],
            aiInsights: null,
            marketContext: null,
            optionChain: { calls: [], puts: [] },
            allExpirations: [],
            selectedExpiration: '',
            isLoadingMarketContext: true
        });
        try {
            const res = await api.get(`/options/expirations/${sym}`);
            const exps = res.data.expirations || [];
            const firstExp = exps.length > 0 ? exps[0] : '';

            set({
                ticker: res.data.ticker,
                spotPrice: res.data.spot_price,
                riskFreeRate: res.data.risk_free_rate,
                allExpirations: exps,
                selectedExpiration: firstExp,
                isLoadingChain: false
            });

            // Auto-cargar la cadena de la primera expiración
            if (firstExp) {
                get().fetchChainForExpiration(sym, firstExp);
            }

            // Fetch Market Context asíncrono
            get().fetchMarketContext(sym);

        } catch (error) {
            console.error("Error al traer Expirations", error);
            set({ isLoadingChain: false, isLoadingMarketContext: false });
        }
    },

    // 1b. Fetch Extended Market Context (Sentiment + YF)
    fetchMarketContext: async (sym) => {
        try {
            const res = await api.get(`/market-context/${sym}`);
            set({ marketContext: res.data, isLoadingMarketContext: false });
        } catch (error) {
            console.error("Error fetching market context:", error);
            set({ isLoadingMarketContext: false });
        }
    },

    // 2. Paso 2: Cargar cadena para UNA expiración específica
    fetchChainForExpiration: async (sym, expiration) => {
        set({ isLoadingExpiration: true, selectedExpiration: expiration });
        try {
            const ticker = sym || get().ticker;
            const res = await api.get(`/options/chain/${ticker}`, {
                params: { expiration }
            });
            set({
                optionChain: res.data.chain || { calls: [], puts: [] },
                spotPrice: res.data.spot_price || get().spotPrice,
                isLoadingExpiration: false
            });
        } catch (error) {
            console.error("Error al traer chain para expiration", error);
            set({ isLoadingExpiration: false });
        }
    },

    // 3. Agregar / Quitar Patas
    addLeg: (leg) => {
        set((state) => ({ legs: [...state.legs, leg] }));
        get()._triggerCalcDebounced();
    },

    removeLeg: (index) => {
        set((state) => ({ legs: state.legs.filter((_, i) => i !== index) }));
        get()._triggerCalcImmediate();
    },

    // 3b. Cargar una estrategia completa de golpe (desde el Recommender)
    loadStrategy: (newLegs) => {
        set({ legs: newLegs });
        get()._triggerCalcImmediate();
    },

    // 4. Sliders con Debounce
    setVolatilityShock: (shock) => {
        set({ volatilityShock: shock });
        get()._triggerCalcDebounced();
    },

    setDaysToSimulate: (days) => {
        set({ daysToSimulate: days });
        get()._triggerCalcDebounced();
    },

    _triggerCalcImmediate: async () => {
        clearTimeout(_calcTimeout);
        await get()._doCalculations();
    },

    _triggerCalcDebounced: () => {
        clearTimeout(_calcTimeout);
        _calcTimeout = setTimeout(() => {
            get()._doCalculations();
        }, 400);
    },

    _doCalculations: async () => {
        const { legs, spotPrice, volatilityShock, daysToSimulate, ticker } = get();

        if (!legs || legs.length === 0) {
            set({ heatmapData: [], aiInsights: null, isLoadingHeatmap: false });
            return;
        }

        // Lock anti-concurrencia: invalidar cálculos anteriores
        const myVersion = ++_calcVersion;

        set({ isLoadingHeatmap: true });

        const payload = {
            underlying_price: spotPrice,
            volatility_shock: volatilityShock,
            days_to_simulate: daysToSimulate,
            legs: legs,
            ticker: ticker || null
        };

        try {
            // Solo heatmap + griegas rápidas (SIN LLM)
            const [heatmapRes, greeksRes] = await Promise.all([
                api.post('/calculations/heatmap', payload),
                api.post('/ai/greeks', payload)
            ]);

            // Si ya hay un cálculo más nuevo, descartamos este
            if (_calcVersion !== myVersion) return;

            set({
                heatmapData: Array.isArray(heatmapRes.data?.heatmap_grid) ? heatmapRes.data.heatmap_grid : [],
                aiInsights: greeksRes.data || null,
                isLoadingHeatmap: false
            });
        } catch (error) {
            console.error("Fallo triggereando calculos", error);
            if (_calcVersion === myVersion) {
                set({ isLoadingHeatmap: false });
            }
        }
    }
}));
