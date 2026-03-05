import React from 'react';

export default function MethodologyModal({ onClose }) {
    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(15, 18, 24, 0.85)', zIndex: 1000,
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            backdropFilter: 'blur(8px)'
        }}>
            <div className="glass-panel" style={{
                width: '85%', maxWidth: '1000px', maxHeight: '85vh',
                overflowY: 'auto', position: 'relative',
                lineHeight: '1.6', fontSize: '0.95rem',
                border: '1px solid rgba(0, 230, 118, 0.3)'
            }}>
                <button onClick={onClose} style={{
                    position: 'absolute', top: '20px', right: '20px',
                    background: 'rgba(239,83,80,0.1)', border: '1px solid rgba(239,83,80,0.5)',
                    color: '#EF5350', fontSize: '1rem', cursor: 'pointer',
                    borderRadius: '50%', width: '30px', height: '30px',
                    display: 'flex', justifyContent: 'center', alignItems: 'center'
                }}>✖</button>

                <h2 style={{ color: '#00E676', marginTop: '10px', fontSize: '1.8rem', borderBottom: '1px solid var(--border-glass)', paddingBottom: '10px' }}>
                    📖 Metodología y Ventaja Competitiva Integral
                </h2>

                <section style={{ marginBottom: '25px' }}>
                    <h3 style={{ color: 'var(--text-primary)' }}>1. Arquitectura y Uso del Sistema</h3>
                    <p style={{ color: 'var(--text-muted)' }}>
                        <strong>OptionStrat AI</strong> es una plataforma de ingeniería financiera enfocada en la simulación predictiva de derivados financieros (Opciones Estilo Americano) y valoración de activos sobre la curva de distribución normal de Black-Scholes-Merton.
                    </p>
                    <p style={{ color: 'var(--text-muted)' }}>
                        <strong>Casos de Uso:</strong>
                        <ul style={{ paddingLeft: '20px' }}>
                            <li>Simulación de estrategias de combinaciones matemáticas complejas (Iron Condors, Strangles, Spreads) ajustando variables macroeconómicas exógenas como la Volatilidad Implícita (Shock Interactivo) y el arrastre degenerativo de los Días Calendario (Theta Decay).</li>
                            <li><strong>Filtrado Institucional:</strong> Uso del "Optimizador de Estrategias" para encontrar oportunidades con riesgo/recompensa asimétricos validados por liquidez real (Volume / Open Interest estricto).</li>
                        </ul>
                    </p>
                </section>

                <section style={{ marginBottom: '25px' }}>
                    <h3 style={{ color: 'var(--text-primary)' }}>2. El Motor Matemático Cuantitativo</h3>
                    <p style={{ color: 'var(--text-muted)' }}>
                        Todo el simulador del <em>Heatmap</em> front-end es proyectado a 250 puntos bidimensionales, donde cada matriz se modela consumiendo la API asíncrona construida en FastAPI con SciPy (Python). La valoración calcula Delta, Gamma, Theta, Vega y Rho integrando tasas libres de riesgo obtenidas dinámicamente de bonos indexados o promedios históricos.
                    </p>
                    <p style={{ color: 'var(--text-muted)' }}>
                        Permite inyectar las propias variables de las "Griegas de Cartera Parcial" consolidadas y agnósticas (por ejemplo, tener Acciones Subyacentes + Puts simultáneamente funciona en simetría perfecta tras parchar el flujo <em>kind="stock"</em> de las fórmulas de Black-Scholes).
                    </p>
                </section>

                <section style={{ marginBottom: '25px' }}>
                    <h3 style={{ color: '#64FFDA' }}>3. OptionStrat AI vs OptionStrat Clásico (El gran salto evolutivo)</h3>
                    <p style={{ color: 'var(--text-muted)' }}>
                        Aunque <em>OptionStrat</em> (el servicio web popular) ha democratizado el P&L numérico de opciones, nuestro desarrollo <strong>OptionStrat AI</strong> se diferencia radicalmente implementando los siguientes pilares inexistentes en el competidor comercial:
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginTop: '15px' }}>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            <h4 style={{ margin: '0 0 10px 0', color: '#00E676' }}>A. LLM Cuantitativo Interactivo</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                                OptionStrat te da números crudos y asume tu expertise. Aquí inyectamos todo el estado de tu cartera al agente <strong>Option Analyst AI (vía OpenAI estructurado)</strong> que redacta una interpretación humana del riesgo de las griegas, avisándote proactivamente si estás sobreexpuesto a riesgos gamma inversos.
                            </p>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            <h4 style={{ margin: '0 0 10px 0', color: '#00E676' }}>B. Cruce con Sentimiento e Insiders</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                                Integración nativa asíncrona con el analizador de datos no estructurados Vader-Sentiment (sobre Finviz News) y movimientos corporativos en la sombra (Insider Trading de C-levels capturados en 13F mediante YahooQuery). El AI sabe si el CEO de Apple acaba de vender USD 40 millones el mismo día que armaste un Call Bullish.
                            </p>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            <h4 style={{ margin: '0 0 10px 0', color: '#00E676' }}>C. Optimizador de Liquidez Estricta</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                                Detecta Spreads fantasmas (con cero pujas OTM en un activo ilíquido) y bloquea estrategias "matemáticamente perfectas" pero "financieramente imposibles". Bloques estrictos a umbrales variables Open Interest &gt; 50 para Conservadores.
                            </p>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                            <h4 style={{ margin: '0 0 10px 0', color: '#00E676' }}>D. Privacidad Criptográfica Total</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                                Corre de forma 100% aislada de <i>Trackers de Venta de Flujo (PFOF)</i> de terceros. Tu brújula de trade es soberana. Tu propia llave API procesa las abstracciones de LLM en contenedores locales Zustand (Frontend).
                            </p>
                        </div>
                    </div>
                </section>

                <section>
                    <h3 style={{ color: 'var(--text-primary)' }}>4. Pruebas y Uso (Ejemplo: Covered Call Clásico)</h3>
                    <ul style={{ color: 'var(--text-muted)', paddingLeft: '20px', lineHeight: '1.8' }}>
                        <li>1. Carga un Ticker institucional <code>(AAPL, SPY, NVDA)</code> e inicializa la cadena.</li>
                        <li>2. Clickea sobre <strong>+100 Acciones (Covered)</strong> directamente desde los botones primarios del panel Builder. Tu inventario físico reflejará el costo Spot.</li>
                        <li>3. Navega por las Calls Out The Money (Ventas / Bids de color verde a lado izquierdo del Grid), garantizando un Strike por encima de la compra.</li>
                        <li>4. Abre la evaluación cruzada. Observa el delta neto acortándose hacia cero y el decaimiento temporal positivo (+Theta).</li>
                    </ul>
                </section>

                <div style={{ textAlign: 'center', marginTop: '30px' }}>
                    <button onClick={onClose} style={{
                        padding: '10px 30px', background: 'var(--profit-gradient)', color: '#000',
                        border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer',
                        fontSize: '1rem'
                    }}>
                        Entendido, Volver a la Terminal
                    </button>
                </div>
            </div>
        </div>
    );
}
