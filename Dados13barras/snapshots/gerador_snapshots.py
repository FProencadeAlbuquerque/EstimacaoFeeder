"""Gerador de dados com vários snapshots por vetor de parâmetros (IEEE 13 barras, linha 650632).

Para cada vetor θ = (r11..r33, x11..x33) sorteado, o trecho RG60–632 recebe essa impedância e o
fluxo de potência é resolvido K vezes, cada vez com as cargas multiplicadas por fatores
independentes U(1-VAR, 1+VAR). Assim θ fica fixo e as correntes do trecho mudam de direção entre
snapshots (desequilíbrio diferente), o que atende ao Corolário 2 (três correntes linearmente
independentes sobre C).

Diferenças em relação ao gerador original (estima_parametros_13_bus_per_phase_separado.ipynb):
  * só a linha 650632 recebe θ (antes o linecode mtx601 era alterado, o que mudava também
    632670, 670671 e 671680);
  * leitura direta pela API do OpenDSS (opendssdirect), sem arredondamento dos CSVs de export;
  * K snapshots por θ, com os fatores de carga e os taps dos reguladores registrados.

Funciona em Windows e Linux:  pip install opendssdirect.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
MASTER = AQUI / 'dss' / 'IEEE13Nodeckt.dss'

# mtx601 original (ohm/milha), linha 650632 com 2000 ft
R_ORIG = np.array([[0.3465, 0.1560, 0.1580], [0.1560, 0.3375, 0.1535], [0.1580, 0.1535, 0.3414]])
X_ORIG = np.array([[1.0179, 0.5017, 0.4236], [0.5017, 1.0478, 0.3849], [0.4236, 0.3849, 1.0348]])
LINHA, COMPRIMENTO_FT = '650632', 2000
PARAMS = ['r11', 'r12', 'r22', 'r13', 'r23', 'r33', 'x11', 'x12', 'x22', 'x13', 'x23', 'x33']
_POS = {'11': (0, 0), '12': (0, 1), '22': (1, 1), '13': (0, 2), '23': (1, 2), '33': (2, 2)}
FASES = 'ABC'


def sortear_thetas(n, nivel, seed=0):
    """Mesmo sorteio do gerador original: normal com desvio relativo `nivel`, depois simetriza."""
    rng = np.random.default_rng(seed)
    th = np.empty((n, 12))
    for i in range(n):
        R = rng.normal(R_ORIG, nivel * R_ORIG)
        X = rng.normal(X_ORIG, nivel * X_ORIG)
        th[i] = [R[_POS[p[1:]]] for p in PARAMS[:6]] + [X[_POS[p[1:]]] for p in PARAMS[6:]]
    return th


def sortear_fatores(n, K, n_cargas, var, seed=1):
    """Fatores de carga independentes por θ, snapshot e carga (mesmo fator para kW e kvar)."""
    rng = np.random.default_rng(seed)
    return rng.uniform(1 - var, 1 + var, size=(n, K, n_cargas))


def _mstr(m):
    return f"({m[0,0]:.10g} | {m[0,1]:.10g} {m[1,1]:.10g} | {m[0,2]:.10g} {m[1,2]:.10g} {m[2,2]:.10g})"


def _theta_para_RX(t):
    R, X = np.zeros((3, 3)), np.zeros((3, 3))
    for k, p in enumerate(PARAMS):
        a, b = _POS[p[1:]]
        M = R if p[0] == 'r' else X
        M[a, b] = M[b, a] = t[k]
    return R, X


def _resolver(dss, theta, fatores, cargas, base):
    dss.Text.Command(f'redirect [{MASTER}]')            # recompila: taps partem sempre do mesmo estado
    R, X = _theta_para_RX(theta)
    dss.Text.Command(f'new linecode.pert nphases=3 basefreq=60 rmatrix={_mstr(R)} '
                     f'xmatrix={_mstr(X)} units=mi')
    dss.Text.Command(f'edit line.{LINHA} linecode=pert length={COMPRIMENTO_FT} units=ft')
    for nome, f in zip(cargas, fatores):
        dss.Loads.Name(nome)
        dss.Loads.kW(base[nome][0] * f)
        dss.Loads.kvar(base[nome][1] * f)
    dss.Solution.Solve()
    reg = {}
    if not dss.Solution.Converged():
        return None
    dss.Circuit.SetActiveElement(f'Line.{LINHA}')
    I = np.array(dss.CktElement.CurrentsMagAng()).reshape(6, 2)
    S = np.array(dss.CktElement.Powers()).reshape(6, 2)
    for j, p in enumerate(FASES):
        reg[f'P1_fase{p}'], reg[f'Q1_fase{p}'] = S[j]
        reg[f'P2_fase{p}'], reg[f'Q2_fase{p}'] = S[3 + j]
    for barra in ['RG60', '632']:
        dss.Circuit.SetActiveBus(barra)
        v = np.array(dss.Bus.VMagAngle()).reshape(3, 2)
        for j in range(3):
            reg[f'V{j+1}_mag_{barra}'], reg[f'V{j+1}_ang_{barra}'] = v[j]
    for j, p in enumerate(FASES):
        reg[f'I1_mag_fase{p}'], reg[f'I1_ang_fase{p}'] = I[j]
        reg[f'I2_mag_fase{p}'], reg[f'I2_ang_fase{p}'] = I[3 + j]
    for r in ['reg1', 'reg2', 'reg3']:
        dss.Transformers.Name(r)
        dss.Transformers.Wdg(2)
        reg[f'tap_{r}'] = dss.Transformers.Tap()
    return reg


def cargas_base():
    import opendssdirect as dss
    dss.Text.Command(f'redirect [{MASTER}]')
    base = {}
    for nome in dss.Loads.AllNames():
        dss.Loads.Name(nome)
        base[nome] = (dss.Loads.kW(), dss.Loads.kvar())
    return base


def _bloco(args):
    """Roda um bloco de θ (usado por multiprocessing; cada processo tem seu próprio OpenDSS)."""
    ids, thetas, fatores = args
    import opendssdirect as dss
    base = cargas_base()
    cargas = list(base)
    linhas = []
    for i, th, F in zip(ids, thetas, fatores):
        for k in range(F.shape[0]):
            reg = _resolver(dss, th, F[k], cargas, base)
            linha = {'theta_id': i, 'snapshot': k, **dict(zip(PARAMS, th)),
                     **{f'fator_{c}': f for c, f in zip(cargas, F[k])}}
            if reg is None:
                linha['convergiu'] = False
            else:
                linha.update(reg)
                linha['convergiu'] = True
            linhas.append(linha)
    return linhas


def gerar(n_theta=10000, K=5, nivel=0.01, var_carga=0.30, seed=0, n_proc=1, bloco=250):
    """Retorna um DataFrame longo: uma linha por (theta_id, snapshot)."""
    n_cargas = len(cargas_base())
    thetas = sortear_thetas(n_theta, nivel, seed)
    fatores = sortear_fatores(n_theta, K, n_cargas, var_carga, seed + 1)
    tarefas = [(np.arange(a, min(a + bloco, n_theta)), thetas[a:a + bloco], fatores[a:a + bloco])
               for a in range(0, n_theta, bloco)]
    if n_proc > 1:
        from multiprocessing import Pool
        with Pool(n_proc) as pool:
            partes = pool.map(_bloco, tarefas)
    else:
        partes = [_bloco(t) for t in tarefas]
    df = pd.DataFrame([l for p in partes for l in p])
    return df.sort_values(['theta_id', 'snapshot']).reset_index(drop=True)
