import React, { useState } from 'react';
import { useStrategyStore } from '../store/strategyStore';
import api from '../api/client';

export default function AiInsights() {
    const { aiInsights, marketContext, isLoadingMarketContext, legs, spotPrice, volatilityShock, daysToSimulate, ticker } = useStrategyStore();
    const [llmText, setLlmText] = useState('');
    const [isLoadingLLM, setIsLoadingLLM] = useState(false);
    const [activeTab, setActiveTab] = useState('ia_risk'); // 'ia_risk', 'fundamental', 'sentiment'

    if (legs.length === 0 && !marketContext && !isLoadingMarketContext) {
        return (
            <section className="glass-panel" style={{ borderLeft: '2px solid rgba(0, 230, 118, 0.3)', width: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <h3 style={{ marginTop: 0 }}>Terminal de Analisis</h3>
                <p style={{ color: 'var(--text-muted)' }}>Construye una posicion o busca un Ticker para comenzar.</p>
            </section>
        );
    }

    // Tab 1 Data (Greeks & IA)
    const greeks = aiInsights?.net_greeks || { delta: 0, gamma: 0, theta: 0, vega: 0 };
    const score = aiInsights?.risk_score || 5;
    const isHighRisk = score > 7;
    const tips = aiInsights?.quick_tips || [];
    const displayLLM = llmText || aiInsights?.llm_analysis || '';

    const handleRequestAI = async () => {
        setIsLoadingLLM(true);
        setLlmText('');
        try {
            const payload = {
                underlying_price: spotPrice,
                volatility_shock: volatilityShock,
                days_to_simulate: daysToSimulate,
                legs: legs,
                ticker: ticker || null,
                market_context: marketContext // Inyectando todo el perfil de sentiment/targets si esta ok
            };
            const res = await api.post('/ai/insights', payload);
            setLlmText(res.data?.llm_analysis || 'Analisis completado sin texto.');
        } catch (e) {
            console.error("AI Error:", e);
            setLlmText('Error al obtener el analisis de IA.');
        } finally {
            setIsLoadingLLM(false);
        }
    };

    const renderTabSelector = () => (
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', marginBottom: '15px' }}>
            <button
                onClick={() => setActiveTab('ia_risk')}
                style={{ flex: 1, padding: '8px 0', border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: activeTab === 'ia_risk' ? 'bold' : 'normal', color: activeTab === 'ia_risk' ? '#64FFDA' : 'var(--text-muted)', borderBottom: activeTab === 'ia_risk' ? '2px solid #64FFDA' : 'none' }}>
                IA & Riesgo
            </button>
            <button
                onClick={() => setActiveTab('fundamental')}
                style={{ flex: 1, padding: '8px 0', border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: activeTab === 'fundamental' ? 'bold' : 'normal', color: activeTab === 'fundamental' ? '#64FFDA' : 'var(--text-muted)', borderBottom: activeTab === 'fundamental' ? '2px solid #64FFDA' : 'none' }}>
                Contexto
            </button>
            <button
                onClick={() => setActiveTab('sentiment')}
                style={{ flex: 1, padding: '8px 0', border: 'none', background: 'transparent', cursor: 'pointer', fontWeight: activeTab === 'sentiment' ? 'bold' : 'normal', color: activeTab === 'sentiment' ? '#64FFDA' : 'var(--text-muted)', borderBottom: activeTab === 'sentiment' ? '2px solid #64FFDA' : 'none' }}>
                Sentimiento
            </button>
        </div>
    );

    const renderIARiskTab = () => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <header>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Metrica de Peligro (1-10):</span>
                    <span className="mono-numbers" style={{
                        background: isHighRisk ? 'rgba(255,82,82,0.2)' : 'rgba(0,200,83,0.2)',
                        color: isHighRisk ? '#FF5252' : '#00C853',
                        padding: '2px 8px', borderRadius: '100px', fontWeight: 'bold'
                    }}>
                        {score}
                    </span>
                </div>
            </header>

            {/* Griegas Netas - SIEMPRE VISIBLES */}
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#FFF' }}>Griegas Netas</h4>
                {legs.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0 }}>Construye una estrategia para ver métricas.</p>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: '#03A9F4', fontSize: '0.8rem', fontWeight: 600 }}>Δ Delta</span>
                            <span className="mono-numbers" style={{ color: greeks.delta < 0 ? '#FF5252' : '#00C853' }}>
                                {greeks.delta > 0 ? '+' : ''}{greeks.delta}
                            </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: '#AB47BC', fontSize: '0.8rem', fontWeight: 600 }}>Γ Gamma</span>
                            <span className="mono-numbers" style={{ color: greeks.gamma < 0 ? '#FF5252' : '#FFF' }}>
                                {greeks.gamma}
                            </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: '#FF9800', fontSize: '0.8rem', fontWeight: 600 }}>Θ Theta</span>
                            <span className="mono-numbers" style={{ color: greeks.theta < 0 ? '#FF5252' : '#00C853' }}>
                                {greeks.theta > 0 ? '+' : ''}{greeks.theta}/dia
                            </span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: '#9C27B0', fontSize: '0.8rem', fontWeight: 600 }}>V Vega</span>
                            <span className="mono-numbers">{greeks.vega}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Quick Tips */}
            {tips.length > 0 && legs.length > 0 && (
                <div>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Veredicto Preliminar</h4>
                    {tips.map((tip, idx) => (
                        <div key={idx} style={{
                            fontSize: '0.85rem', lineHeight: '1.4', marginBottom: '8px',
                            paddingLeft: '10px', borderLeft: '2px solid rgba(255,255,255,0.2)'
                        }}>
                            {tip}
                        </div>
                    ))}
                </div>
            )}

            {/* AI Action Button */}
            <button
                onClick={handleRequestAI}
                disabled={isLoadingLLM || legs.length === 0}
                style={{
                    width: '100%', padding: '9px',
                    background: isLoadingLLM ? 'rgba(100,255,218,0.05)' : 'rgba(100,255,218,0.08)',
                    border: '1px solid rgba(100,255,218,0.3)', color: '#64FFDA', borderRadius: '6px',
                    cursor: isLoadingLLM || legs.length === 0 ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold', fontSize: '0.82rem', transition: 'all 0.2s ease', opacity: legs.length === 0 ? 0.3 : 1
                }}
            >
                {isLoadingLLM ? '⏳ Consultando Analista...' : '🤖 Evaluacion Estrategica Global'}
            </button>

            {/* AI Result Box */}
            {displayLLM && (
                <div style={{
                    background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px',
                    border: '1px solid rgba(100,255,218,0.15)', flex: 1, overflowY: 'auto', maxHeight: '250px'
                }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '0.8rem', color: '#64FFDA' }}>Analisis Extendido IA</h4>
                    <p style={{ fontSize: '0.82rem', lineHeight: '1.55', color: 'var(--text-primary)', margin: 0, whiteSpace: 'pre-wrap' }}>
                        {displayLLM}
                    </p>
                </div>
            )}
        </div>
    );

    const renderFundamentalTab = () => {
        if (isLoadingMarketContext) {
            return <p style={{ color: 'var(--text-muted)' }}>Descargando parametros financieros fundamentales...</p>;
        }
        if (!marketContext) {
            return <p style={{ color: '#EF5350' }}>No se pudo obtener el contexto (Network Error).</p>;
        }

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                    <h4 style={{ margin: '0 0 10px 0', color: '#00C853' }}>{marketContext.symbol} Fundamentals</h4>
                    <p style={{ margin: '0 0 10px 0', fontSize: '0.8rem', lineHeight: '1.5', color: 'var(--text-muted)' }}>
                        {marketContext.long_business_summary || 'Informacion de negocio no disponible en tiempo real.'}
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Spot</span>
                            <strong className="mono-numbers" style={{ color: '#FFF' }}>${marketContext.current_price?.toFixed(2) || '-'}</strong>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Recommendation</span>
                            <strong style={{ color: '#FFF', textTransform: 'capitalize' }}>{marketContext.recommendation_key?.replace('_', ' ') || '-'}</strong>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Target Mean</span>
                            <strong className="mono-numbers" style={{ color: '#00C853' }}>${marketContext.target_mean?.toFixed(2) || '-'}</strong>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ color: 'var(--text-muted)' }}>P/E Forward</span>
                            <strong className="mono-numbers" style={{ color: '#FFF' }}>{marketContext.forward_pe?.toFixed(2) || '-'}</strong>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    const renderSentimentTab = () => {
        if (isLoadingMarketContext) {
            return <p style={{ color: 'var(--text-muted)' }}>Procesando NLP y flujos algoritmicos...</p>;
        }
        if (!marketContext) {
            return <p style={{ color: '#EF5350' }}>No se pudo conectar a los oraculos de sentimiento.</p>;
        }

        const vaderColor = marketContext.sentiment_score > 0.05 ? '#00C853' : (marketContext.sentiment_score < -0.05 ? '#EF5350' : '#FF9800');

        return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                    <h4 style={{ margin: '0 0 10px 0', color: '#FFF' }}>VADER Finviz Sentiment</h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                            width: '40px', height: '40px', borderRadius: '50%', background: vaderColor,
                            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontWeight: 'bold', fontSize: '0.9rem'
                        }}>
                            {(marketContext.sentiment_score * 100).toFixed(0)}
                        </div>
                        <div style={{ flex: 1 }}>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Puntuación Algoritmica Compuesta (15 Días)</span>
                            <div style={{ width: '100%', height: '4px', background: '#333', marginTop: '5px', borderRadius: '2px' }}>
                                <div style={{ width: `${(marketContext.sentiment_score + 1) * 50}%`, height: '100%', background: vaderColor, borderRadius: '2px' }} />
                            </div>
                        </div>
                    </div>
                </div>

                {marketContext.recent_news?.length > 0 && (
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '0.85rem', color: '#FFF' }}>Titulares Recientes</h4>
                        <ul style={{ margin: 0, paddingLeft: '15px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {marketContext.recent_news.slice(0, 4).map((n, i) => (
                                <li key={i} style={{ marginBottom: '6px', lineHeight: '1.3' }}>"{n}"</li>
                            ))}
                        </ul>
                    </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: 'rgba(0,200,83,0.05)', border: '1px solid rgba(0,200,83,0.2)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                        <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)' }}>Insider Purchases</span>
                        <span className="mono-numbers" style={{ fontSize: '1.2rem', color: '#00C853', fontWeight: 'bold' }}>{marketContext.insider_purchases || 0}</span>
                    </div>
                    <div style={{ background: 'rgba(239,83,80,0.05)', border: '1px solid rgba(239,83,80,0.2)', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                        <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-muted)' }}>Insider Sales</span>
                        <span className="mono-numbers" style={{ fontSize: '1.2rem', color: '#EF5350', fontWeight: 'bold' }}>{marketContext.insider_sales || 0}</span>
                    </div>
                </div>

                {marketContext.top_insiders?.length > 0 && (
                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '0.85rem', color: '#FFF' }}>Top Flujo Insiders Reciente</h4>
                        <ul style={{ margin: 0, paddingLeft: '0', listStyle: 'none', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {marketContext.top_insiders.map((ins, i) => (
                                <li key={i} style={{ marginBottom: '8px', lineHeight: '1.3', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <strong style={{ color: '#FFF' }}>{ins.name}</strong> <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>({ins.position})</span><br />
                                    <span style={{ color: ins.shares_traded > 0 ? '#00C853' : '#EF5350', fontFamily: 'var(--font-mono)' }}>
                                        {ins.shares_traded > 0 ? '+' : ''}{ins.shares_traded.toLocaleString()} acciones
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        );
    };

    return (
        <section className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', borderLeft: `2px solid ${isHighRisk ? '#FF5252' : '#00C853'}`, overflowY: 'auto' }}>
            {renderTabSelector()}

            <div style={{ flex: 1, paddingRight: '5px' }}>
                {activeTab === 'ia_risk' && renderIARiskTab()}
                {activeTab === 'fundamental' && renderFundamentalTab()}
                {activeTab === 'sentiment' && renderSentimentTab()}
            </div>
        </section>
    );

}
