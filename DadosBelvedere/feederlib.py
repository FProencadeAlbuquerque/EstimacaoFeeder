"""Biblioteca do alimentador do Belvedere: carga dos dados, ruído de µPMU/TI, modelos e referências.

Reconstruída a partir da feederlib.py usada nos resultados do paper (conversa de out/2026), com duas
mudanças: (1) só o caso do Belvedere, lendo as três planilhas desta pasta (níveis 0,01 a 0,29);
(2) modelo de ruído de D'Antona et al. (IEEE TIM, 2026): erro da µPMU aleatório por amostra e erro
dos TIs sistemático (um sorteio por canal, fixo em todas as amostras).
"""
import math
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

PARAMS = ['r11', 'r12', 'r22', 'r13', 'r23', 'r33', 'x11', 'x12', 'x22', 'x13', 'x23', 'x33']
GRUPOS = {'Reactances': ['x11', 'x12', 'x22', 'x13', 'x23', 'x33'],
          'Self resistances': ['r11', 'r22', 'r33'],
          'Mutual resistances': ['r12', 'r13', 'r23']}
POS = {0: (0, 0), 1: (0, 1), 2: (1, 1), 3: (0, 2), 4: (1, 2), 5: (2, 2)}
SEED = 0
CRAD_TO_DEG = 0.01 * 180 / math.pi
B_S, B_R = '59911939827572667mt', '59912191827572000mt'   # terminal emissor (s) e receptor (r)

FILES = {0: '0_0_09_resultados_perturbacoes_potencia.xlsx',
         1: '0_1_0_19_resultados_perturbacoes_potencia.xlsx',
         2: '0_2_0_29_resultados_perturbacoes_potencia.xlsx'}
NIVEIS = [round(0.01 * k, 2) for k in range(1, 30)]


# ---------------------------------------------------------------- dados
def _fasor(m, a):
    return np.asarray(m) * np.exp(1j * np.deg2rad(np.asarray(a)))


def carregar(nivel, pasta='.'):
    """Lê a aba pert_<nivel> e devolve fasores (n, 3) dos dois terminais e os parâmetros."""
    df = pd.read_excel(f'{pasta}/{FILES[int(round(nivel * 100)) // 10]}', sheet_name=f'pert_{nivel:.2f}')
    V1 = np.stack([_fasor(df[f'V{k}_mag_{B_S}'], df[f'V{k}_ang_{B_S}']) for k in (1, 2, 3)], 1)
    V2 = np.stack([_fasor(df[f'V{k}_mag_{B_R}'], df[f'V{k}_ang_{B_R}']) for k in (1, 2, 3)], 1)
    I1 = np.stack([_fasor(df[f'I1_mag_fase{p}'], df[f'I1_ang_fase{p}']) for p in 'ABC'], 1)
    I2 = np.stack([_fasor(df[f'I2_mag_fase{p}'], df[f'I2_ang_fase{p}']) for p in 'ABC'], 1)
    # a planilha só tem P, Q trifásicos totais; as potências por fase vêm de V·conj(I)
    return dict(nivel=nivel, Y=df[PARAMS].values, V1=V1, V2=V2, I1=I1, I2=I2)


def carregar_ieee13(path):
    """IEEE 13 barras (linha RG60–632), usado nas comparações do paper. As tensões do CSV estão
    arredondadas (0,01 V e 0,1°); P, Q e I por fase têm precisão maior, então V = 1000·S/conj(I)."""
    df = pd.read_csv(path)
    I1 = np.stack([_fasor(df[f'I1_mag_fase{p}'], df[f'I1_ang_fase{p}']) for p in 'ABC'], 1)
    I2 = np.stack([_fasor(df[f'I2_mag_fase{p}'], df[f'I2_ang_fase{p}']) for p in 'ABC'], 1)
    S1 = np.stack([df[f'P1_fase{p}'] + 1j * df[f'Q1_fase{p}'] for p in 'ABC'], 1)
    S2 = np.stack([df[f'P2_fase{p}'] + 1j * df[f'Q2_fase{p}'] for p in 'ABC'], 1)
    return dict(nivel=0.01, Y=df[PARAMS].values, I1=I1, I2=I2,
                V1=1000 * S1 / np.conj(I1), V2=1000 * S2 / np.conj(I2))


# ---------------------------------------------------------------- física
def matriz_Z(theta):
    r11, r12, r22, r13, r23, r33, x11, x12, x22, x13, x23, x33 = theta.T
    R = np.stack([np.stack([r11, r12, r13], -1), np.stack([r12, r22, r23], -1), np.stack([r13, r23, r33], -1)], -2)
    X = np.stack([np.stack([x11, x12, x13], -1), np.stack([x12, x22, x23], -1), np.stack([x13, x23, x33], -1)], -2)
    return R + 1j * X


def ajustar_ell(Y, dV, I):
    ZI = np.einsum('nij,nj->ni', matriz_Z(Y), I)
    return np.real(np.vdot(ZI.ravel(), dV.ravel()) / np.vdot(ZI.ravel(), ZI.ravel()))


def jacobiano(I, ell):
    Jc = np.zeros((3, 12), complex)
    for k, (a, b) in POS.items():
        for i, j in {(a, b), (b, a)}:
            Jc[i, k] += ell * I[j]
            Jc[i, 6 + k] += 1j * ell * I[j]
    return np.vstack([Jc.real, Jc.imag])


# ---------------------------------------------------------------- ruído µPMU + TI (D'Antona et al., 2026)
RUIDO = dict(pmu_mag=0.002, ti_mag=0.010, pmu_ang=0.2 * CRAD_TO_DEG,
             tp_ang=1.2 * CRAD_TO_DEG, tc_ang=1.8 * CRAD_TO_DEG)
CANAIS = ['V1', 'V2', 'I1', 'I2']


def erros_ti(seed):
    """Erros sistemáticos dos TIs: um sorteio por canal (fasor × fase), em módulo (fração) e ângulo (graus)."""
    rng = np.random.default_rng(seed)
    out = {}
    for c in CANAIS:
        a_ti = RUIDO['tp_ang'] if c[0] == 'V' else RUIDO['tc_ang']
        out[c] = (rng.uniform(-RUIDO['ti_mag'], RUIDO['ti_mag'], 3), rng.uniform(-a_ti, a_ti, 3))
    return out


def erros_pmu(n, K, rng):
    """Erro aleatório da µPMU, já com a média de K snapshots sincronizados (cai com 1/√K)."""
    out = {}
    for c in CANAIS:
        em = sum(rng.uniform(-RUIDO['pmu_mag'], RUIDO['pmu_mag'], (n, 3)) for _ in range(K)) / K
        ea = sum(rng.uniform(-RUIDO['pmu_ang'], RUIDO['pmu_ang'], (n, 3)) for _ in range(K)) / K
        out[c] = (em, ea)
    return out


def aplicar_ruido(d, e_pmu, e_ti, alpha):
    """Fasores medidos: módulo·(1 + α(ε_PMU + b_TI)), ângulo + α(ε_PMU + b_TI)."""
    out = {}
    for c in CANAIS:
        F = d[c]
        em = alpha * (e_pmu[c][0] + e_ti[c][0])
        ea = alpha * (e_pmu[c][1] + e_ti[c][1])
        out[c] = _fasor(np.abs(F) * (1 + em), np.angle(F, deg=True) + ea)
    return out


def sigmas(alpha, K):
    """Desvios-padrão (módulo relativo; ângulos em rad) do erro total por amostra: µPMU com média de K
    snapshots + TI (sistemático, não reduzido pela média), tratado como desconhecido."""
    s = lambda pmu, ti: alpha * math.sqrt((pmu ** 2 / K + ti ** 2) / 3)
    sm = s(RUIDO['pmu_mag'], RUIDO['ti_mag'])
    sav = s(RUIDO['pmu_ang'], RUIDO['tp_ang']) * math.pi / 180
    sai = s(RUIDO['pmu_ang'], RUIDO['tc_ang']) * math.pi / 180
    return sm, sav, sai


def cov_ruido_dV(V1, V2, I, alpha, K):
    """Covariância linearizada do erro em [Re ΔV; Im ΔV] por amostra (tensões + correntes propagadas)."""
    sm, sav, sai = sigmas(alpha, K)
    n = len(V1)
    R = np.zeros((n, 6, 6))
    for k in range(n):
        for V in (V1[k], V2[k]):
            for p in range(3):
                a, b = V[p].real, V[p].imag
                R[k][np.ix_([p, p + 3], [p, p + 3])] += np.array(
                    [[a * a * sm * sm + b * b * sav * sav, a * b * (sm * sm - sav * sav)],
                     [a * b * (sm * sm - sav * sav), b * b * sm * sm + a * a * sav * sav]])
    g = np.abs(V1 - V2) / np.maximum(np.abs(I), 1e-9)
    for k in range(n):
        for p in range(3):
            s2 = (g[k, p] * np.abs(I[k, p])) ** 2 * (sm * sm + sai * sai) / 2
            R[k, p, p] += s2
            R[k, p + 3, p + 3] += s2
    return R


# ---------------------------------------------------------------- entradas por posição das µPMUs
CONFIGS = {'both': 'µPMU at both terminals', 'sending': 'µPMU at sending end only',
           'receiving': 'µPMU at receiving end only'}


def montar_X(F, config):
    """|V|, ∠V, |I|, ∠I e P, Q por fase (V·conj(I)) no(s) terminal(is) medido(s)."""
    def bloco(V, I):
        S = V * np.conj(I)
        return [np.abs(V), np.angle(V, deg=True), np.abs(I), np.angle(I, deg=True), S.real, S.imag]
    blocos = []
    if config in ('both', 'sending'):
        blocos += bloco(F['V1'], F['I1'])
    if config in ('both', 'receiving'):
        blocos += bloco(F['V2'], F['I2'])
    return np.hstack(blocos)


# ---------------------------------------------------------------- modelos e métricas
def novos_modelos(rapido=False):
    m = {
        'Ridge': Ridge(alpha=1e-3),
        'MLP': MLPRegressor(hidden_layer_sizes=(128, 128), alpha=1e-4, max_iter=1000, early_stopping=True,
                            n_iter_no_change=30, random_state=SEED),
        'LightGBM': MultiOutputRegressor(lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31,
                                                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                                                           random_state=SEED, verbose=-1, n_jobs=2)),
    }
    if not rapido:
        m['RandomForest'] = MultiOutputRegressor(RandomForestRegressor(n_estimators=100, max_depth=20,
                                                                       max_samples=0.8, n_jobs=2,
                                                                       random_state=SEED))
    return m


def mape(Yv, Yp):
    return 100 * np.mean(np.abs(Yp - Yv) / np.abs(Yv), axis=0)


def bayes_e_limite(dV, I, Yte, mu, Sigma, ell, R=None):
    """Média a posteriori (equação da linha) e MAPE mínimo teórico (aproximação gaussiana)."""
    med = np.empty((len(dV), 12))
    sig = np.empty((len(dV), 12))
    for n in range(len(dV)):
        J = jacobiano(I[n], ell)
        y = np.concatenate([dV[n].real, dV[n].imag])
        S = J @ Sigma @ J.T + (0 if R is None else R[n])
        G = Sigma @ J.T @ np.linalg.inv(S)
        med[n] = mu + G @ (y - J @ mu)
        sig[n] = np.sqrt(np.clip(np.diag(Sigma - G @ J @ Sigma), 0, None))
    return med, 100 * math.sqrt(2 / math.pi) * np.mean(sig / np.abs(Yte), axis=0)


# ---------------------------------------------------------------- experimento
def experimento(d, config='both', alpha=0.0, K=1, rapido=False, modelos=None, limite=True,
                it_seed=1, it_seeds_teste=tuple(range(2, 12))):
    """Treina e testa (80/20) os modelos; devolve o MAPE (%) por parâmetro.

    Com ruído (alpha > 0): treino e teste usam os TIs de `it_seed`; as colunas '<modelo> (unseen ITs)'
    repetem o teste com as mesmas amostras e o mesmo ruído da µPMU, mas com os TIs de `it_seeds_teste`
    (média dos MAPEs), que é o cenário de campo.
    """
    Y = d['Y']
    n = len(Y)
    idx_tr, idx_te = train_test_split(np.arange(n), test_size=0.2, random_state=SEED)
    if alpha > 0:
        e_pmu = erros_pmu(n, K, np.random.default_rng(SEED))
        Fn = aplicar_ruido(d, e_pmu, erros_ti(it_seed), alpha)
    else:
        Fn = {c: d[c] for c in CANAIS}
    X = montar_X(Fn, config)
    keep = X[idx_tr].std(0) > 0
    sx, sy = StandardScaler().fit(X[idx_tr][:, keep]), StandardScaler().fit(Y[idx_tr])
    Xtr, Xte = sx.transform(X[idx_tr][:, keep]), sx.transform(X[idx_te][:, keep])
    Xu = []
    if alpha > 0 and it_seeds_teste:
        for s in it_seeds_teste:
            Xs = montar_X(aplicar_ruido(d, e_pmu, erros_ti(s), alpha), config)
            Xu.append(sx.transform(Xs[idx_te][:, keep]))
    Yte = Y[idx_te]
    out, tempos = {}, {}
    for nome, m in (modelos or novos_modelos(rapido)).items():
        t0 = time.time()
        m.fit(Xtr, sy.transform(Y[idx_tr]))
        out[nome] = mape(Yte, sy.inverse_transform(m.predict(Xte)))
        if Xu:
            out[f'{nome} (unseen ITs)'] = np.mean(
                [mape(Yte, sy.inverse_transform(m.predict(x))) for x in Xu], axis=0)
        tempos[nome] = time.time() - t0
    tab = pd.DataFrame(out, index=PARAMS)
    if limite and config == 'both':
        ell = ajustar_ell(Y[idx_tr], (d['V1'] - d['V2'])[idx_tr], d['I1'][idx_tr])
        mu, Sigma = Y[idx_tr].mean(0), np.diag(Y[idx_tr].var(0))
        R = None if alpha == 0 else cov_ruido_dV(d['V1'][idx_te], d['V2'][idx_te], d['I1'][idx_te], alpha, K)
        med, lim = bayes_e_limite((Fn['V1'] - Fn['V2'])[idx_te], Fn['I1'][idx_te], Yte, mu, Sigma, ell, R)
        tab['Line-equation Bayes'] = mape(Yte, med)
        tab['Line-equation bound'] = lim
    return tab, tempos
