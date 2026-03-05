import React from 'react';
import { useStrategyStore } from '../store/strategyStore';

export default function Builder() {
    const {
        optionChain, legs, addLeg, removeLeg, spotPrice, ticker,
        allExpirations, selectedExpiration, fetchChainForExpiration,
        isLoadingExpiration
    } = useStrategyStore();

    const handleAddLeg = (type, action, strike, premium, expiration, volume = 0, openInterest = 0) => {
        addLeg({
            type,
            action,
            strike: Number(strike),
            expiration: expiration || selectedExpiration || '2026-12-18',
            qty: 1,
            premium: Number(premium || 0.0),
            volume: Number(volume),
            open_interest: Number(openInterest)
        });
    };

    const getUnifiedChain = () => {
        if (!optionChain?.calls && !optionChain?.puts) return [];

        const strikesMap = new Map();

        (optionChain.calls || []).forEach(c => {
            strikesMap.set(c.strike, { ...strikesMap.get(c.strike), call: c });
        });
        (optionChain.puts || []).forEach(p => {
            strikesMap.set(p.strike, { ...strikesMap.get(p.strike), put: p });
        });

        let allStrikes = Array.from(strikesMap.keys());
        allStrikes.sort((a, b) => Math.abs(a - spotPrice) - Math.abs(b - spotPrice));

        const closestStrikes = allStrikes.slice(0, 10).sort((a, b) => a - b);

        return closestStrikes.map(strike => ({
            strike,
            call: strikesMap.get(strike)?.call || null,
            put: strikesMap.get(strike)?.put || null
        }));
    };

    const unifiedChain = getUnifiedChain();

    const safeBid = (val) => {
        const n = Number(val);
        return isFinite(n) && n > 0 ? n.toFixed(2) : '-';
    };

    const safeAsk = (val) => {
        const n = Number(val);
        return isFinite(n) && n > 0 ? n.toFixed(2) : '-';
    };

    return (
        <section className="glass-panel" style={{ height: '100%', overflowY: 'auto' }}>
            <h3 style={{ marginTop: 0 }}>Strategy Builder</h3>

            {/* Controles de Subyacente (Spot) */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                <button
                    onClick={() => handleAddLeg('stock', 'buy', spotPrice, spotPrice, selectedExpiration, 0, 0)}
                    disabled={!ticker}
                    style={{ flex: 1, padding: '8px', background: 'rgba(0,200,83,0.1)', border: '1px solid rgba(0,200,83,0.4)', color: '#00C853', borderRadius: '4px', cursor: ticker ? 'pointer' : 'not-allowed', fontSize: '0.8rem', fontWeight: 'bold' }}>
                    +100 Acciones (Covered)
                </button>
                <button
                    onClick={() => handleAddLeg('stock', 'sell', spotPrice, spotPrice, selectedExpiration, 0, 0)}
                    disabled={!ticker}
                    style={{ flex: 1, padding: '8px', background: 'rgba(239,83,80,0.1)', border: '1px solid rgba(239,83,80,0.4)', color: '#EF5350', borderRadius: '4px', cursor: ticker ? 'pointer' : 'not-allowed', fontSize: '0.8rem', fontWeight: 'bold' }}>
                    -100 Acciones (Short)
                </button>
            </div>

            {/* Posiciones activas */}
            <div style={{ marginBottom: '20px', borderBottom: '1px solid var(--border-glass)', paddingBottom: '15px' }}>
                <h4 style={{ color: 'var(--text-muted)' }}>Opciones Activas ({legs.length})</h4>
                {legs.length === 0 && <p style={{ fontSize: '0.85rem' }}>Haz click en Bid (Sell) o Ask (Buy) para añadir una posición.</p>}

                {legs.map((leg, idx) => (
                    <div key={idx} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        background: leg.action === 'buy' ? 'rgba(0,200,83,0.1)' : 'rgba(239,83,80,0.1)',
                        padding: '8px', borderRadius: '6px', marginBottom: '8px', fontSize: '0.9rem'
                    }}>
                        <span>
                            <strong style={{ textTransform: 'uppercase' }}>{leg.action}</strong>{' '}
                            {leg.qty} {leg.type.toUpperCase()} ${leg.strike}{' '}
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                @${Number(leg.premium).toFixed(2)} | {leg.expiration}
                            </span>
                        </span>
                        <button
                            onClick={() => removeLeg(idx)}
                            style={{ background: 'transparent', border: 'none', color: '#EF5350', cursor: 'pointer', fontSize: '1rem' }}
                        >
                            ✕
                        </button>
                    </div>
                ))}
            </div>

            {/* Selector de Expiración — TODAS las fechas disponibles */}
            {allExpirations.length > 0 && (
                <div style={{ marginBottom: '15px', padding: '0 5px' }}>
                    <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginRight: '10px' }}>
                        Expiración ({allExpirations.length} disponibles):
                    </label>
                    <select
                        value={selectedExpiration}
                        onChange={(e) => fetchChainForExpiration(ticker, e.target.value)}
                        style={{
                            background: 'rgba(255,255,255,0.05)', color: '#FFF',
                            border: '1px solid var(--border-glass)', borderRadius: '4px',
                            padding: '4px 8px', outline: 'none', cursor: 'pointer',
                            fontFamily: 'var(--font-mono)'
                        }}
                    >
                        {allExpirations.map(exp => (
                            <option key={exp} value={exp} style={{ background: '#1A1D24' }}>
                                {exp}
                            </option>
                        ))}
                    </select>
                    {isLoadingExpiration && (
                        <span style={{ marginLeft: '10px', color: '#00E676', fontSize: '0.8rem' }}>⏳ Cargando...</span>
                    )}
                </div>
            )}

            {/* Unified Chain Table (T-Quote) */}
            <div style={{ display: 'flex', flexDirection: 'column', marginTop: '10px', fontFamily: 'var(--font-mono)' }}>
                {/* Headers */}
                <div style={{ display: 'flex', borderBottom: '1px solid var(--border-glass)', paddingBottom: '3px', marginBottom: '5px', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 'bold' }}>
                    <span style={{ flex: 1, textAlign: 'center', color: '#00C853' }}>CALL BID</span>
                    <span style={{ flex: 1, textAlign: 'center', color: '#EF5350' }}>CALL ASK</span>
                    <span style={{ width: '35px', textAlign: 'center' }}>V/OI</span>

                    <span style={{ width: '60px', textAlign: 'center', color: '#FFF' }}>STRIKE</span>

                    <span style={{ width: '35px', textAlign: 'center' }}>V/OI</span>
                    <span style={{ flex: 1, textAlign: 'center', color: '#00C853' }}>PUT BID</span>
                    <span style={{ flex: 1, textAlign: 'center', color: '#EF5350' }}>PUT ASK</span>
                </div>

                {isLoadingExpiration ? (
                    <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Cargando cadena...</p>
                ) : unifiedChain.length === 0 ? (
                    <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Sin datos</p>
                ) : unifiedChain.map((row) => (
                    <div key={row.strike} style={{ display: 'flex', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.03)', padding: '4px 0', fontSize: '0.8rem' }}>

                        {/* CALL SIDE */}
                        <div style={{ flex: 1, display: 'flex', gap: '3px' }}>
                            {row.call ? (
                                <>
                                    <button onClick={() => handleAddLeg('call', 'sell', row.strike, row.call.bid, row.call.expirationDate, row.call.volume, row.call.openInterest)}
                                        style={{ flex: 1, background: 'rgba(0,200,83,0.1)', color: '#00C853', border: '1px solid rgba(0,200,83,0.3)', borderRadius: '4px', cursor: 'pointer', padding: '4px 0' }}>
                                        {safeBid(row.call.bid)}
                                    </button>
                                    <button onClick={() => handleAddLeg('call', 'buy', row.strike, row.call.ask, row.call.expirationDate, row.call.volume, row.call.openInterest)}
                                        style={{ flex: 1, background: 'rgba(239,83,80,0.1)', color: '#EF5350', border: '1px solid rgba(239,83,80,0.3)', borderRadius: '4px', cursor: 'pointer', padding: '4px 0' }}>
                                        {safeAsk(row.call.ask)}
                                    </button>
                                    <div style={{ width: '35px', fontSize: '0.55rem', color: '#B0BEC5', textAlign: 'right', display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingRight: '4px' }}>
                                        <div style={{ color: '#FFF' }}>{row.call.volume || 0}</div>
                                        <div>{row.call.openInterest || 0}</div>
                                    </div>
                                </>
                            ) : (
                                <div style={{ flex: 1, textAlign: 'center', color: 'var(--text-muted)' }}>-</div>
                            )}
                        </div>

                        {/* STRIKE CENTERED */}
                        <div style={{ width: '60px', textAlign: 'center', fontWeight: 'bold', fontSize: '0.85rem', color: '#FFF', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', padding: '3px 0', margin: '0 4px' }}>
                            {row.strike}
                        </div>

                        {/* PUT SIDE */}
                        <div style={{ flex: 1, display: 'flex', gap: '3px' }}>
                            {row.put ? (
                                <>
                                    <div style={{ width: '35px', fontSize: '0.55rem', color: '#B0BEC5', textAlign: 'left', display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingLeft: '4px' }}>
                                        <div style={{ color: '#FFF' }}>{row.put.volume || 0}</div>
                                        <div>{row.put.openInterest || 0}</div>
                                    </div>
                                    <button onClick={() => handleAddLeg('put', 'sell', row.strike, row.put.bid, row.put.expirationDate, row.put.volume, row.put.openInterest)}
                                        style={{ flex: 1, background: 'rgba(0,200,83,0.1)', color: '#00C853', border: '1px solid rgba(0,200,83,0.3)', borderRadius: '4px', cursor: 'pointer', padding: '4px 0' }}>
                                        {safeBid(row.put.bid)}
                                    </button>
                                    <button onClick={() => handleAddLeg('put', 'buy', row.strike, row.put.ask, row.put.expirationDate, row.put.volume, row.put.openInterest)}
                                        style={{ flex: 1, background: 'rgba(239,83,80,0.1)', color: '#EF5350', border: '1px solid rgba(239,83,80,0.3)', borderRadius: '4px', cursor: 'pointer', padding: '4px 0' }}>
                                        {safeAsk(row.put.ask)}
                                    </button>
                                </>
                            ) : (
                                <div style={{ flex: 1, textAlign: 'center', color: 'var(--text-muted)' }}>-</div>
                            )}
                        </div>

                    </div>
                ))}
            </div>
        </section>
    );
}
