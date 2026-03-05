import { useState } from 'react';
import { useStrategyStore } from './store/strategyStore';
import { Builder, Heatmap, AiInsights, Recommender, Mascot, MethodologyModal } from './components';
import './index.css';

function App() {
  const { ticker, spotPrice, isLoadingChain, fetchExpirations } = useStrategyStore();
  const [inputTicker, setInputTicker] = useState('');
  const [showMethodology, setShowMethodology] = useState(false);

  const handleSearch = (e) => {
    if (e.key === 'Enter' && inputTicker.trim()) {
      fetchExpirations(inputTicker.trim().toUpperCase());
    }
  };

  const hasData = ticker && ticker.length > 0;

  return (
    <div style={{ padding: '20px', minHeight: '100vh', display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Modales Flotantes */}
      {showMethodology && <MethodologyModal onClose={() => setShowMethodology(false)} />}

      {/* Header */}
      <header className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>OptionStrat <span style={{ color: 'var(--profit-gradient)' }}>AI</span></h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>Advanced Derivatives Simulator</p>
        </div>
        <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: '15px' }}>

          <button
            onClick={() => setShowMethodology(true)}
            style={{
              background: 'rgba(0, 230, 118, 0.1)', border: '1px solid rgba(0, 230, 118, 0.4)',
              color: '#00E676', padding: '8px 12px', borderRadius: '4px', outline: 'none',
              cursor: 'pointer', fontFamily: 'var(--font-mono)', fontWeight: 'bold'
            }}
          >
            📚 Metodología y Doc
          </button>

          <input
            type="text"
            value={inputTicker}
            onChange={(e) => setInputTicker(e.target.value)}
            onKeyDown={handleSearch}
            placeholder="Ticker (AAPL)..."
            style={{
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)',
              color: '#FFF', padding: '8px 12px', borderRadius: '4px', outline: 'none',
              textTransform: 'uppercase', width: '140px', fontFamily: 'var(--font-mono)'
            }}
          />
          {hasData && (
            <h2 style={{ margin: 0 }}>
              {ticker.toUpperCase()}{' '}
              <span className="mono-numbers" style={{ color: '#00E676' }}>${spotPrice.toFixed(2)}</span>
            </h2>
          )}
        </div>
      </header>

      {/* Spinner de carga */}
      {isLoadingChain && (
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '20px', minHeight: '60vh' }}>
          <div style={{
            width: '50px', height: '50px', border: '3px solid rgba(255,255,255,0.1)',
            borderTop: '3px solid #00E676', borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Cargando expiraciones y precio spot...</p>
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Pantalla de bienvenida */}
      {!isLoadingChain && !hasData && (
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '20px', minHeight: '60vh' }}>
          <Mascot />
          <h2 style={{ margin: 0, color: 'var(--text-primary)', fontWeight: 300, fontSize: '1.8rem' }}>
            Bienvenido a <strong>OptionStrat AI</strong>
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', maxWidth: '500px', textAlign: 'center', lineHeight: '1.6' }}>
            Escribe un símbolo de ticker en el campo de búsqueda y presiona <strong>Enter</strong> para comenzar.
          </p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
            {['AAPL', 'TSLA', 'NVDA', 'SPY'].map(sym => (
              <button
                key={sym}
                onClick={() => { setInputTicker(sym); fetchExpirations(sym); }}
                style={{
                  background: 'rgba(0,230,118,0.08)', border: '1px solid rgba(0,230,118,0.3)',
                  color: '#00E676', padding: '8px 18px', borderRadius: '6px', cursor: 'pointer',
                  fontFamily: 'var(--font-mono)', fontWeight: 'bold', fontSize: '0.9rem',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={(e) => { e.target.style.background = 'rgba(0,230,118,0.2)'; }}
                onMouseLeave={(e) => { e.target.style.background = 'rgba(0,230,118,0.08)'; }}
              >
                {sym}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Grid principal - Fila 1: Builder + Heatmap + AI */}
      {!isLoadingChain && hasData && (
        <>
          <main style={{ display: 'grid', gridTemplateColumns: 'minmax(330px, 1.2fr) minmax(500px, 2fr) minmax(280px, 1fr)', gap: '20px', flex: 1 }}>
            <section style={{ height: '100%', overflowY: 'auto' }}>
              <Builder />
            </section>
            <section style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Heatmap />
            </section>
            <section style={{ height: '100%' }}>
              <AiInsights />
            </section>
          </main>

          {/* Fila 2: Optimizador de Estrategias (full width) */}
          <Recommender />
        </>
      )}
    </div>
  );
}

export default App;
