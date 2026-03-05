import React, { useMemo } from 'react';
import { useStrategyStore } from '../store/strategyStore';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid } from 'recharts';

// Función segura para formatear dinero — nunca lanza excepción
const formatMoney = (val) => {
    const n = Number(val);
    if (!isFinite(n) || isNaN(n)) return '$0.00';
    return `$${n.toFixed(2)}`;
};

export default function Heatmap() {
    const {
        heatmapData, isLoadingHeatmap, legs,
        daysToSimulate, setDaysToSimulate,
        volatilityShock, setVolatilityShock
    } = useStrategyStore();

    // ══════════════════════════════════════════════════════════════════
    // TODOS LOS HOOKS DEBEN IR AQUÍ ARRIBA — ANTES de cualquier return
    // ══════════════════════════════════════════════════════════════════

    const safeHeatmapData = Array.isArray(heatmapData) ? heatmapData : [];

    // 1. chartData: memoizado
    const chartData = useMemo(() => {
        if (safeHeatmapData.length === 0) {
            return [{ price_sim: 100, pnl: 0 }, { price_sim: 101, pnl: 0 }];
        }

        const t_days_uniq = [...new Set(safeHeatmapData.map(d => d.t_days))];
        if (t_days_uniq.length === 0) {
            return [{ price_sim: 100, pnl: 0 }, { price_sim: 101, pnl: 0 }];
        }

        const safeDays = Number(daysToSimulate) || 0;
        const target_t_day = t_days_uniq.reduce((prev, curr) =>
            Math.abs(curr - safeDays) < Math.abs(prev - safeDays) ? curr : prev
        );

        const filtered = safeHeatmapData
            .filter(d => d.t_days === target_t_day)
            .map(d => ({
                price_sim: Number(d.price_sim) || 0,
                pnl: isFinite(Number(d.pnl)) ? Number(d.pnl) : 0
            }))
            .sort((a, b) => a.price_sim - b.price_sim);

        return filtered.length > 0 ? filtered : [{ price_sim: 100, pnl: 0 }, { price_sim: 101, pnl: 0 }];
    }, [safeHeatmapData, daysToSimulate]);

    // 2. Métricas derivadas: memoizado
    const { maxProfit, maxLoss, breakEvens, netPremium } = useMemo(() => {
        const defaults = { maxProfit: 0, maxLoss: 0, breakEvens: [], netPremium: 0 };
        if (!chartData || chartData.length <= 1 || !legs || legs.length === 0) return defaults;

        try {
            const pnls = chartData.map(d => d.pnl).filter(v => isFinite(v));
            if (pnls.length === 0) return defaults;

            const minPnl = Math.min(...pnls);
            const maxPnl = Math.max(...pnls);

            const bes = [];
            for (let i = 1; i < chartData.length; i++) {
                const prevPnl = chartData[i - 1].pnl;
                const currPnl = chartData[i].pnl;
                if (isFinite(prevPnl) && isFinite(currPnl) && Math.sign(prevPnl) !== Math.sign(currPnl)) {
                    const avg = (chartData[i - 1].price_sim + chartData[i].price_sim) / 2;
                    if (isFinite(avg)) bes.push(avg);
                }
            }

            let premium = 0;
            legs.forEach(leg => {
                const p = Number(leg.premium) || 0;
                const q = Number(leg.qty) || 1;
                const cost = p * q * 100;
                if (leg.action === 'buy') premium -= cost;
                else premium += cost;
            });

            return {
                maxProfit: isFinite(maxPnl) ? maxPnl : 0,
                maxLoss: isFinite(minPnl) ? minPnl : 0,
                breakEvens: bes,
                netPremium: isFinite(premium) ? premium : 0
            };
        } catch {
            return defaults;
        }
    }, [chartData, legs]);

    // 3. maxSimDays: memoizado
    const maxSimDays = useMemo(() => {
        if (!legs || legs.length === 0) return 30;
        const today = new Date();
        try {
            const dtes = legs.map(leg => {
                if (!leg.expiration) return 30;
                const expDate = new Date(leg.expiration);
                if (isNaN(expDate.getTime())) return 30;
                const diffMs = expDate.getTime() - today.getTime();
                return Math.max(Math.ceil(diffMs / (1000 * 60 * 60 * 24)), 1);
            });
            const min = Math.min(...dtes);
            return isFinite(min) && min > 0 ? min : 30;
        } catch {
            return 30;
        }
    }, [legs]);

    const currentSimDays = Math.min(Number(daysToSimulate) || 1, maxSimDays);

    const gradientOffset = useMemo(() => {
        if (maxProfit <= 0) return 0;
        if (maxLoss >= 0) return 1;
        return maxProfit / (maxProfit - maxLoss);
    }, [maxProfit, maxLoss]);
    const splitOff = `${(gradientOffset * 100).toFixed(2)}%`;

    // ══════════════════════════════════════════════════════════════════
    // DESDE AQUÍ PUEDEN IR LOS RETURNS CONDICIONALES (después de hooks)
    // ══════════════════════════════════════════════════════════════════

    // Sin legs → placeholder
    if (!legs || legs.length === 0) {
        return (
            <section className="glass-panel" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ color: 'var(--text-muted)' }}>Agrega opciones a tu estrategia para visualizar el Payoff 2D.</p>
            </section>
        );
    }

    // Cargando → spinner
    if (isLoadingHeatmap) {
        return (
            <section className="glass-panel" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ color: 'var(--profit-gradient)' }}>Calculando super-superficie de Black Scholes...</p>
            </section>
        );
    }

    // ─── Render principal ────────────────────────────────────────────
    return (
        <section className="glass-panel" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <h3 style={{ marginTop: 0 }}>Payoff Simulator</h3>

            {/* Controles */}
            <div style={{ display: 'flex', gap: '20px', marginBottom: '15px', paddingBottom: '15px', borderBottom: '1px solid var(--border-glass)' }}>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                        Shock de Volatilidad (IV): {((Number(volatilityShock) || 0) * 100).toFixed(0)}%
                    </label>
                    <input
                        type="range" min="-0.5" max="0.5" step="0.05"
                        value={volatilityShock}
                        onChange={(e) => setVolatilityShock(Number(e.target.value))}
                        style={{ width: '100%', accentColor: '#00C853' }}
                    />
                </div>
                <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                        Días de Evolución: {currentSimDays} días (Límite: {maxSimDays})
                    </label>
                    <input
                        type="range" min="1" max={maxSimDays} step="1"
                        value={currentSimDays}
                        onChange={(e) => setDaysToSimulate(Number(e.target.value))}
                        style={{ width: '100%', accentColor: '#00C853' }}
                    />
                </div>
            </div>

            {/* Panel de Métricas */}
            <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: '15px', background: 'rgba(255,255,255,0.02)', padding: '10px 15px', borderRadius: '8px', border: '1px solid var(--border-glass)', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Net Premium</span>
                    <span className="mono-numbers" style={{ color: netPremium >= 0 ? '#00C853' : '#EF5350', fontWeight: 'bold', fontSize: '0.9rem' }}>
                        {netPremium >= 0 ? '+' : ''}{formatMoney(netPremium)}
                    </span>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Max Loss</span>
                    <span className="mono-numbers" style={{ color: '#EF5350', fontWeight: 'bold', fontSize: '0.9rem' }}>
                        {formatMoney(maxLoss)}
                    </span>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Break-Even(s)</span>
                    <span className="mono-numbers" style={{ color: 'var(--text-primary)', fontWeight: 'bold', fontSize: '0.9rem' }}>
                        {breakEvens.length > 0 ? breakEvens.map(be => formatMoney(be)).join(' / ') : '-'}
                    </span>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Max Profit</span>
                    <span className="mono-numbers" style={{ color: '#00C853', fontWeight: 'bold', fontSize: '0.9rem' }}>
                        {formatMoney(maxProfit)}
                    </span>
                </div>
            </div>

            {/* Gráfico AreaChart */}
            <div style={{ flex: 1, minHeight: '300px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <defs>
                            <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#00C853" stopOpacity={0.4} />
                                <stop offset={splitOff} stopColor="#00C853" stopOpacity={0.05} />
                                <stop offset={splitOff} stopColor="#EF5350" stopOpacity={0.05} />
                                <stop offset="100%" stopColor="#EF5350" stopOpacity={0.4} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="price_sim" stroke="var(--text-muted)" tickFormatter={(val) => `$${val}`} />
                        <YAxis stroke="var(--text-muted)" tickFormatter={(val) => `$${val}`} />

                        <Tooltip
                            contentStyle={{ background: 'rgba(26, 29, 36, 0.9)', border: '1px solid var(--border-glass)', borderRadius: '8px', color: '#FFF' }}
                            itemStyle={{ fontFamily: 'var(--font-mono)' }}
                            formatter={(value) => [formatMoney(value), 'P&L']}
                            labelFormatter={(label) => `Subyacente: $${label}`}
                        />

                        <ReferenceLine y={0} stroke="rgba(255,255,255,0.4)" strokeWidth={1} strokeDasharray="4 4" />

                        <Area
                            type="linear"
                            dataKey="pnl"
                            stroke="#64FFDA"
                            fill="url(#splitColor)"
                            strokeWidth={2.5}
                            dot={false}
                            activeDot={{ r: 5, fill: '#FFF' }}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

        </section>
    );
}
