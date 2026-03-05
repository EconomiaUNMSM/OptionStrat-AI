
import numpy as np
from scipy.stats import norm
from typing import Union, Tuple

# -------------------------
# Black-Scholes-Merton (BSM)
# -------------------------

def bsm_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0, kind: str = "call") -> float:
    """
    Calcula el precio de una opción Europea usando Black-Scholes-Merton.
    """
    if kind == "stock":
        return float(S)
        
    if T <= 0:
        return max(0.0, (S - K) if kind == "call" else (K - S))
    if sigma <= 0:
        return max(0.0, (S - K) if kind == "call" else (K - S))

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if kind == "call":
        return float(S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
    else:
        return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1))

def bsm_greeks(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0, kind: str = "call") -> dict:
    """
    Calcula Delta, Gamma, Theta, Vega, Rho usando BSM.
    """
    if kind == "stock":
        return {"delta": 1.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    
    pdf_d1 = norm.pdf(d1)
    cdf_d1 = norm.cdf(d1)
    cdf_minus_d1 = norm.cdf(-d1)
    cdf_d2 = norm.cdf(d2)
    cdf_minus_d2 = norm.cdf(-d2)

    gamma = (np.exp(-q * T) * pdf_d1) / (S * sigma * sqrt_T)
    vega = S * np.exp(-q * T) * pdf_d1 * sqrt_T / 100.0  # Scaled for 1% change

    if kind == "call":
        delta = np.exp(-q * T) * cdf_d1
        
        # Theta Call
        term1 = - (S * sigma * np.exp(-q * T) * pdf_d1) / (2 * sqrt_T)
        term2 = - r * K * np.exp(-r * T) * cdf_d2
        term3 = q * S * np.exp(-q * T) * cdf_d1
        theta = (term1 + term2 + term3) / 365.0
        
        rho = (K * T * np.exp(-r * T) * cdf_d2) / 100.0
    else:
        # Delta Put (negative)
        delta = -np.exp(-q * T) * cdf_minus_d1
        
        # Theta Put
        term1 = - (S * sigma * np.exp(-q * T) * pdf_d1) / (2 * sqrt_T)
        term2 = r * K * np.exp(-r * T) * cdf_minus_d2
        term3 = - q * S * np.exp(-q * T) * cdf_minus_d1
        theta = (term1 + term2 + term3) / 365.0
        
        rho = (-K * T * np.exp(-r * T) * cdf_minus_d2) / 100.0

    return {
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega),
        "rho": float(rho)
    }

# -------------------------
# Binomial Tree (American Support)
# -------------------------

def binomial_tree_price(S: float, K: float, T: float, r: float, sigma: float, N: int = 100, 
                        q: float = 0.0, kind: str = "call", style: str = "american") -> float:
    """
    Valoración por Árbol Binomial (Cox-Ross-Rubinstein).
    Soporta ejercicio Americano.
    """
    if T <= 0:
        return max(0.0, (S - K) if kind == "call" else (K - S))
    
    dt = T / N
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp((r - q) * dt) - d) / (u - d)
    disc = np.exp(-r * dt)

    # Pre-compute asset prices at maturity
    ST = S * d**np.arange(N, -1, -1) * u**np.arange(0, N + 1)
    
    # Initialize values at maturity
    if kind == "call":
        C = np.maximum(0, ST - K)
    else:
        C = np.maximum(0, K - ST)

    # Backward induction
    for i in range(N - 1, -1, -1):
        C = disc * (p * C[1:] + (1 - p) * C[:-1]) # Propagación hacia atrás
        if style == "american":
            # Recalcular precios del subyacente en este paso
            Si = S * d**np.arange(i, -1, -1) * u**np.arange(0, i + 1)
            if kind == "call":
                exercise = np.maximum(0, Si - K)
            else:
                exercise = np.maximum(0, K - Si)
            C = np.maximum(C, exercise)
            
    return float(C[0])

# -------------------------
# Trinomial Tree (More precise)
# -------------------------

def trinomial_tree_price(S: float, K: float, T: float, r: float, sigma: float, N: int = 100,
                         q: float = 0.0, kind: str = "call", style: str = "american") -> float:
    """
    Valoración por Árbol Trinomial. Generalmente converge más rápido que el Binomial.
    """
    if T <= 0:
        return max(0.0, (S - K) if kind == "call" else (K - S))

    dt = T / N
    dx = sigma * np.sqrt(3 * dt)
    nu = r - q - 0.5 * sigma**2
    
    pu = 0.5 * ((sigma**2 * dt + nu**2 * dt**2) / dx**2 + (nu * dt) / dx)
    pd = 0.5 * ((sigma**2 * dt + nu**2 * dt**2) / dx**2 - (nu * dt) / dx)
    pm = 1.0 - pu - pd
    disc = np.exp(-r * dt)

    # Grid de precios
    m = 2 * N + 1
    # spots centrados en S
    # S * exp(j * dx) donde j va de -N a N
    center_idx = N
    idxs = np.arange(-N, N + 1)
    ST = S * np.exp(idxs * dx)

    if kind == "call":
        C = np.maximum(0, ST - K)
    else:
        C = np.maximum(0, K - ST)

    # Backward induction
    for i in range(N - 1, -1, -1):
        # En trinomial reducimos 2 nodos por paso (ends)
        # C[j] depende de C[j+1] (up), C[j] (mid), C[j-1] (down) en indices relativos del paso anterior?
        # Implementación vectorizada simplificada:
        # Los nodos válidos en paso i son 2*i + 1. 
        # C[j] = disc * (pu * C[j+2] + pm * C[j+1] + pd * C[j])
        
        # Slice views
        C_down = C[:-2]
        C_mid = C[1:-1]
        C_up = C[2:]
        
        C = disc * (pu * C_up + pm * C_mid + pd * C_down)
        
        if style == "american":
            # Recompute S logic
            idxs_i = np.arange(-i, i + 1)
            Si = S * np.exp(idxs_i * dx)
            if kind == "call":
                exercise = np.maximum(0, Si - K)
            else:
                exercise = np.maximum(0, K - Si)
            C = np.maximum(C, exercise)
            
    return float(C[0])
