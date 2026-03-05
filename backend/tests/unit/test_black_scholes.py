import pytest
import math
from app.core.black_scholes import bsm_price, bsm_greeks

def test_bsm_price_call_in_the_money():
    # Parámetros estáticos conocidos:
    # S = 100, K = 90, T = 0.5 (6 meses), r = 0.05, sigma = 0.2, q = 0.0
    # Esperamos que el precio del call sea significativamente mayor a su valor intrínseco (10)
    S = 100.0
    K = 90.0
    T = 0.5
    r = 0.05
    sigma = 0.2
    
    price = bsm_price(S, K, T, r, sigma, kind="call")
    
    # Valor matemáticamente verificado: 13.4985
    assert math.isclose(price, 13.4985, rel_tol=1e-3)

def test_bsm_price_put_out_of_the_money():
    # S = 100, K = 90, T = 0.5 , r = 0.05, sigma = 0.2, q = 0.0
    S = 100.0
    K = 90.0
    T = 0.5
    r = 0.05
    sigma = 0.2
    
    price = bsm_price(S, K, T, r, sigma, kind="put")
    
    # Valor matemáticamente verificado: 1.2764
    assert math.isclose(price, 1.2764, rel_tol=1e-3)

def test_bsm_greeks_delta():
    S = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.2
    
    greeks_call = bsm_greeks(S, K, T, r, sigma, kind="call")
    greeks_put = bsm_greeks(S, K, T, r, sigma, kind="put")
    
    # El Delta de un call ATM a 1 año suele estar cerca de 0.63
    assert 0.5 < greeks_call["delta"] < 0.7
    # La relación Put-Call parity para el Delta: Delta(put) = Delta(call) - exp(-q*T)
    # Como q=0, Delta(put) = Delta(call) - 1
    assert math.isclose(greeks_put["delta"], greeks_call["delta"] - 1.0, abs_tol=1e-5)
    
def test_expiration_zero_days():
    S = 100.0
    K = 90.0
    T = 0.0 # Vencimiento hoy
    r = 0.05
    sigma = 0.2
    
    price = bsm_price(S, K, T, r, sigma, kind="call")
    # Para un call in the money expirando hoy, el precio debe ser S - K
    assert math.isclose(price, 10.0, rel_tol=1e-5)
