import numpy as np
from datetime import date
from typing import List, Dict
from app.schemas.strategy_models import StrategyState
from app.core.black_scholes import bsm_price

class StrategyBuilder:
    @staticmethod
    def generate_heatmap_grid(state: StrategyState) -> Dict:
        """
        Genera el grid multidimensional iterando el motor matemático (Black-Scholes).
        Cruza variaciones de precio spot y días transcurridos para mapear el P&L (Profit & Loss).
        """
        spot = state.underlying_price
        legs = state.legs
        days_to_sim = state.days_to_simulate
        vol_shock = state.volatility_shock
        
        grid = []
        
        # 1. Definir Crédito/Débito inicial de la estrategia
        initial_cost = 0.0
        for leg in legs:
            # En opciones en USA, 1 contrato = 100 acciones
            cost = leg.premium * leg.qty * 100
            if leg.action == "buy":
                initial_cost -= cost # Pagamos (Débito)
            else: 
                initial_cost += cost # Cobramos (Crédito)
                
        # 2. Definir Vectores de iteración para el Heatmap
        base_prices = list(np.linspace(spot * 0.75, spot * 1.25, 250))
        
        # Puntos críticos (obligatorios para dibujar el "piso" exacto de la "V")
        critical_points = [spot] + [leg.strike for leg in legs]
        
        # Asegurarnos de que el heatmap cubre todos los strikes si están muy OTM
        min_critical = min(critical_points) if critical_points else spot
        max_critical = max(critical_points) if critical_points else spot
        
        extra_prices = []
        if min_critical < spot * 0.75:
            extra_prices.extend(list(np.linspace(min_critical * 0.85, spot * 0.75, 40)))
        if max_critical > spot * 1.25:
            extra_prices.extend(list(np.linspace(spot * 1.25, max_critical * 1.15, 40)))
            
        all_prices = base_prices + extra_prices + critical_points
        
        # Eliminar redundancias y ordenar para el gráfico de área
        price_steps = sorted(list(set(round(p, 2) for p in all_prices)))
        
        # 3. Definir Líneas de tiempo (5 intervalos desde hoy hasta days_to_sim)
        if days_to_sim > 0:
            time_steps = np.linspace(0, days_to_sim, 5, dtype=int)
        else:
            time_steps = [0]
            
        today = date.today()
        max_pnl = float('-inf')
        min_pnl = float('inf')
        
        # 4. Iterar sobre Tiempo(T) y Precio(S) inyectando a Black-Scholes
        for t_days in time_steps:
            for sim_price in price_steps:
                total_sim_value = 0.0
                
                for leg in legs:
                    # Encontrar los días faltantes asumiendo que avanzamos en el tiempo (t_days pasaron)
                    days_remaining = (leg.expiration - today).days - t_days
                    T_years = max(days_remaining / 365.25, 0.0)
                    
                    # Asumimos una TLR genérica para el simulador rápido (5%)
                    r = 0.05
                    # En una fase v2, la Volatilidad Implícita (IV) vendrá propia del leg en vez de fija.
                    # Se suma el shock interactivo del usuario sobre la IV base hipotética (30%)
                    sigma = max(0.30 + vol_shock, 0.01)
                    
                    # Motor Core: bsm_price (Importado de tu modulo_opciones)
                    sim_leg_price = bsm_price(S=sim_price, K=leg.strike, T=T_years, r=r, sigma=sigma, kind=leg.type)
                    
                    # Multiplicador del contrato
                    leg_value = sim_leg_price * leg.qty * 100
                    
                    if leg.action == "buy":
                        total_sim_value += leg_value # Tenemos el derecho (Largo)
                    else:
                        total_sim_value -= leg_value # Tenemos la obligación (Corto)
                
                # Rentabilidad = Valor Simulado de la Posición + Crédito/Débito Inicial
                pnl = total_sim_value + initial_cost
                
                max_pnl = max(max_pnl, pnl)
                min_pnl = min(min_pnl, pnl)
                
                grid.append({
                    "price_sim": round(float(sim_price), 2),
                    "t_days": int(t_days),
                    "pnl": round(float(pnl), 2)
                })
                
        return {
            "max_profit": max_pnl,
            "max_loss": min_pnl,
            "heatmap_grid": grid
        }
