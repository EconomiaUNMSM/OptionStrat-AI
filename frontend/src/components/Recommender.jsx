import { useState } from 'react';
import { useStrategyStore } from '../store/strategyStore';
import api from '../api/client';

const BIAS_OPTIONS = [
    { value: 'bullish', label: '🟢 Alcista', color: '#00C853' },
    { value: 'neutral', label: '🟡 Neutral', color: '#FFD600' },
    { value: 'bearish', label: '🔴 Bajista', color: '#EF5350' }
];

const RISK_OPTIONS = [
    { value: 'conservative', label: 'Conservador', desc: '~85% POP' },
    { value: 'balanced', label: 'Balanceado', desc: '~80% POP' },
    { value: 'aggressive', label: 'Agresivo', desc: '~70% POP' }
];

export default function Recommender() {
    const { ticker, spotPrice, loadStrategy, selectedExpiration } = useStrategyStore();

    const [bias, setBias] = useState('neutral');
    const [riskProfile, setRiskProfile] = useState('balanced');
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [loadedIdx, setLoadedIdx] = useState(null);

    const handleSearch = async () => {
        if (!ticker) return;
        setIsLoading(true);
        setError(null);
        setResults([]);
        setLoadedIdx(null);

        try {
            const res = await api.get(`/options/recommend/${ticker}`, {
                params: { bias, risk_profile: riskProfile }
            });
            setResults(res.data.recommendations || []);
            if ((res.data.recommendations || []).length === 0) {
                setError('No se encontraron estrategias viables para esta configuración.');
            }
        } catch (e) {
            console.error(e);
            setError('Error al buscar estrategias. Intenta de nuevo.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleLoadStrategy = (strat, idx) => {
        // Inyectar TODAS las legs de golpe (atómico, 1 solo cálculo)
        const allLegs = strat.legs.map(leg => ({
            strike: leg.strike,
            type: leg.type,
            action: leg.action,
            premium: leg.premium,
            qty: leg.qty || 1,
            expiration: leg.expiration || selectedExpiration,
            volume: leg.volume || 0,
            open_interest: leg.open_interest || 0
        }));
        loadStrategy(allLegs);
        setLoadedIdx(idx);
    };

    const formatMoney = (val) => {
        if (val === 'Unlimited' || val === Infinity) return '∞';
        if (typeof val !== 'number' || !isFinite(val)) return '-';
        return `$${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    const biasColor = BIAS_OPTIONS.find(b => b.value === bias)?.color || '#FFF';

    return (
        <section className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>
                    🔍 Optimizador de Estrategias
                </h3>
                {ticker && (
                    <span className="mono-numbers" style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {ticker} @ ${spotPrice?.toFixed(2)}
                    </span>
                )}
            </div>

            {/* Controles */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {/* Bias Selector */}
                <div style={{ flex: 1, minWidth: '140px' }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                        Sesgo Direccional
                    </label>
                    <div style={{ display: 'flex', gap: '4px' }}>
                        {BIAS_OPTIONS.map(opt => (
                            <button
                                key={opt.value}
                                onClick={() => setBias(opt.value)}
                                style={{
                                    flex: 1,
                                    padding: '6px 4px',
                                    fontSize: '0.75rem',
                                    fontWeight: bias === opt.value ? 'bold' : 'normal',
                                    background: bias === opt.value ? `${opt.color}22` : 'rgba(255,255,255,0.03)',
                                    border: `1px solid ${bias === opt.value ? opt.color : 'var(--border-glass)'}`,
                                    color: bias === opt.value ? opt.color : 'var(--text-muted)',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s ease'
                                }}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Risk Profile Selector */}
                <div style={{ flex: 1, minWidth: '140px' }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '5px' }}>
                        Perfil de Riesgo
                    </label>
                    <select
                        value={riskProfile}
                        onChange={(e) => setRiskProfile(e.target.value)}
                        style={{
                            width: '100%',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-glass)',
                            color: '#FFF',
                            padding: '7px 8px',
                            borderRadius: '4px',
                            fontSize: '0.85rem',
                            cursor: 'pointer'
                        }}
                    >
                        {RISK_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label} ({opt.desc})</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Botón de búsqueda */}
            <button
                onClick={handleSearch}
                disabled={!ticker || isLoading}
                style={{
                    width: '100%',
                    padding: '10px',
                    background: ticker ? `linear-gradient(135deg, ${biasColor}44, ${biasColor}22)` : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${ticker ? biasColor : 'var(--border-glass)'}`,
                    color: ticker ? biasColor : 'var(--text-muted)',
                    borderRadius: '6px',
                    cursor: ticker ? 'pointer' : 'not-allowed',
                    fontWeight: 'bold',
                    fontSize: '0.9rem',
                    transition: 'all 0.2s ease'
                }}
            >
                {isLoading ? '⏳ Buscando...' : `Buscar Estrategias ${BIAS_OPTIONS.find(b => b.value === bias)?.label || ''}`}
            </button>

            {/* Error */}
            {error && (
                <div style={{ padding: '10px', background: 'rgba(239,83,80,0.08)', border: '1px solid rgba(239,83,80,0.3)', borderRadius: '6px', color: '#EF5350', fontSize: '0.85rem' }}>
                    {error}
                </div>
            )}

            {/* Resultados */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '400px', overflowY: 'auto' }}>
                {results.map((strat, idx) => (
                    <div
                        key={idx}
                        style={{
                            padding: '12px',
                            background: loadedIdx === idx ? 'rgba(0,200,83,0.06)' : 'rgba(255,255,255,0.02)',
                            border: `1px solid ${loadedIdx === idx ? '#00C853' : 'var(--border-glass)'}`,
                            borderRadius: '8px',
                            transition: 'all 0.2s ease'
                        }}
                    >
                        {/* Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontWeight: 'bold', fontSize: '0.95rem', color: '#FFF' }}>
                                {strat.name}
                            </span>
                            <span style={{
                                fontSize: '0.7rem',
                                padding: '2px 8px',
                                borderRadius: '10px',
                                background: strat.sentiment === 'bullish' ? '#00C85322' : strat.sentiment === 'bearish' ? '#EF535022' : '#FFD60022',
                                color: strat.sentiment === 'bullish' ? '#00C853' : strat.sentiment === 'bearish' ? '#EF5350' : '#FFD600',
                                border: `1px solid ${strat.sentiment === 'bullish' ? '#00C85366' : strat.sentiment === 'bearish' ? '#EF535066' : '#FFD60066'}`,
                                textTransform: 'uppercase',
                                fontWeight: 'bold'
                            }}>
                                {strat.sentiment}
                            </span>
                        </div>

                        {/* Legs */}
                        <div style={{ marginBottom: '8px' }}>
                            {strat.legs.map((leg, li) => (
                                <div key={li} style={{ fontSize: '0.78rem', color: 'var(--text-muted)', padding: '2px 0', fontFamily: 'var(--font-mono)' }}>
                                    <span style={{ color: leg.action === 'sell' ? '#EF5350' : '#00C853', fontWeight: 'bold' }}>
                                        {leg.action === 'sell' ? 'SELL' : 'BUY'}
                                    </span>
                                    {' '}
                                    <span style={{ textTransform: 'uppercase' }}>{leg.type}</span>
                                    {' $'}{leg.strike.toFixed(0)}
                                    {' @ $'}{leg.premium.toFixed(2)}
                                    <span style={{ color: 'rgba(255,255,255,0.3)', marginLeft: '6px' }}>
                                        {leg.expiration}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Métricas */}
                        {strat.metrics && (
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '10px' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Net Premium</span>
                                    <span className="mono-numbers" style={{ color: '#00C853', fontWeight: 'bold', fontSize: '0.85rem' }}>
                                        {formatMoney(strat.metrics.net_premium)}
                                    </span>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>Max Loss</span>
                                    <span className="mono-numbers" style={{ color: '#EF5350', fontWeight: 'bold', fontSize: '0.85rem' }}>
                                        {formatMoney(strat.metrics.max_loss)}
                                    </span>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase' }}>ROC</span>
                                    <span className="mono-numbers" style={{ color: '#64FFDA', fontWeight: 'bold', fontSize: '0.85rem' }}>
                                        {strat.metrics.roc_percent?.toFixed(1)}%
                                    </span>
                                </div>
                            </div>
                        )}

                        {/* Botón para cargar al simulador */}
                        <button
                            onClick={() => handleLoadStrategy(strat, idx)}
                            disabled={loadedIdx === idx}
                            style={{
                                width: '100%',
                                padding: '7px',
                                background: loadedIdx === idx ? 'rgba(0,200,83,0.15)' : 'rgba(100,255,218,0.08)',
                                border: `1px solid ${loadedIdx === idx ? '#00C853' : 'rgba(100,255,218,0.3)'}`,
                                color: loadedIdx === idx ? '#00C853' : '#64FFDA',
                                borderRadius: '5px',
                                cursor: loadedIdx === idx ? 'default' : 'pointer',
                                fontWeight: 'bold',
                                fontSize: '0.8rem',
                                transition: 'all 0.15s ease'
                            }}
                        >
                            {loadedIdx === idx ? '✓ Cargada al Simulador' : '⚡ Llevar a Simulator'}
                        </button>
                    </div>
                ))}
            </div>
        </section>
    );
}
