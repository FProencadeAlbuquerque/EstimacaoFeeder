"""Experimentos do IEEE 13 barras com janelas de W pontos de operação (snapshots de carga) por θ.

Usa a base de `gerador_snapshots.py` (cada θ resolvido em 5 pontos de operação) e o mesmo pipeline
do paper (feederlib): divisão 80/20 por θ, entradas padronizadas, Ridge, MLP, LightGBM e RandomForest.

* W = 1: só o ponto de operação 0 de cada θ (como no dataset antigo);
* W = 5: as entradas dos 5 pontos de operação concatenadas.

Ruído (D'Antona et al., 2026): µPMU aleatória, sorteada para cada ponto de operação e reduzida por 1/√K
quando K amostras sincronizadas do mesmo ponto são promediadas; TIs com erro sistemático, sorteado uma vez
por canal (IT_SEED) e igual em todas as amostras e pontos de operação, no treino e no teste.

A referência pela equação da linha empilha as W equações ΔV⁽ᵏ⁾ = ℓ Z I⁽ᵏ⁾ e trata o erro dos TIs como
desconhecido; como ele é o mesmo nos W pontos de operação, a covariância do ruído inclui essa correlação.
"""
import math
import sys
import time
import gc
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent.parent / 'DadosBelvedere'))
import gerador_snapshots as g   # noqa: E402
import feederlib as fl          # noqa: E402

SEED, IT_SEED = 0, 1
ARQ = AQUI / 'snapshots_0.01_K5.csv.gz'
ARQ_CUIABA = AQUI.parent.parent / 'DadosBelvedere' / 'snapshots_0.01_K5.csv.gz'
ELL = g.COMPRIMENTO_FT / 5280                       # IEEE 13: milhas (θ em Ω/mi)
CASOS = {
    # barras dos terminais nas colunas de tensão
    'ieee13': dict(arq=ARQ, b1='RG60', b2='632'),
    # alimentador de Cuiabá (trecho 13806387, 7,13 m; θ em Ω/km). Os 5 pontos de operação multiplicam as
    # cargas de cada fase por fatores fixos; a capacitância de um trecho de 7 m é desprezível (Y/2 = 0)
    'cuiaba': dict(arq=ARQ_CUIABA, b1='barra1', b2='barra2'),
}


def carregar(caso='ieee13'):
    c = CASOS[caso]
    df = pd.read_csv(c['arq']).sort_values(['theta_id', 'snapshot'])
    n, P = df.theta_id.nunique(), df.snapshot.nunique()
    fas = lambda pares: np.stack([fl._fasor(df[m], df[a]) for m, a in pares], 1).reshape(n, P, 3)
    d = dict(caso=caso, Y=df.groupby('theta_id')[g.PARAMS].first().values, n=n, P=P,
             V1=fas([(f'V{j}_mag_{c["b1"]}', f'V{j}_ang_{c["b1"]}') for j in (1, 2, 3)]),
             V2=fas([(f'V{j}_mag_{c["b2"]}', f'V{j}_ang_{c["b2"]}') for j in (1, 2, 3)]),
             I1=fas([(f'I1_mag_fase{p}', f'I1_ang_fase{p}') for p in 'ABC']),
             I2=fas([(f'I2_mag_fase{p}', f'I2_ang_fase{p}') for p in 'ABC']))
    if caso == 'ieee13':
        import opendssdirect as dss
        dss.Text.Command(f'redirect [{g.MASTER}]')
        dss.Lines.Name(g.LINHA)
        C = np.array(dss.Lines.CMatrix()).reshape(3, 3) * dss.Lines.Length() * 1e-9    # F no trecho
        d['Y_meio'], d['ell'] = 1j * 2 * np.pi * 60 * C / 2, ELL
    else:
        d['Y_meio'], d['ell'] = np.zeros((3, 3)), float(df['comprimento_km'].iloc[0])
    d['idx_tr'], d['idx_te'] = train_test_split(np.arange(n), test_size=0.2, random_state=SEED)
    return d


def com_ruido(d, alpha, K):
    """Fasores medidos (n, P, 3): µPMU por ponto de operação (média de K) + TIs fixos (IT_SEED)."""
    if alpha == 0:
        return {c: d[c] for c in fl.CANAIS}
    n, P = d['n'], d['P']
    plano = {c: d[c].reshape(-1, 3) for c in fl.CANAIS}
    e_pmu = fl.erros_pmu(n * P, K, np.random.default_rng(SEED))
    out = fl.aplicar_ruido(plano, e_pmu, fl.erros_ti(IT_SEED), alpha)
    return {c: out[c].reshape(n, P, 3) for c in fl.CANAIS}


def entradas(F, W, config):
    n = F['V1'].shape[0]
    Fp = {c: F[c][:, :W].reshape(-1, 3) for c in fl.CANAIS}
    return fl.montar_X(Fp, config).reshape(n, -1)


# ---------------------------------------------------------------- referência pela equação da linha
def _desvios(alpha, K):
    """Desvios-padrão dos termos uniformes: (µPMU aleatório já com média de K, TI sistemático),
    em fração (módulo) e radianos (ângulo), para tensão e corrente."""
    r, u = fl.RUIDO, lambda x: alpha * x / math.sqrt(3)
    rad = math.pi / 180
    pmu = dict(m=u(r['pmu_mag']) / math.sqrt(K), a=u(r['pmu_ang']) * rad / math.sqrt(K))
    ti_v = dict(m=u(r['ti_mag']), a=u(r['tp_ang']) * rad)
    ti_i = dict(m=u(r['ti_mag']), a=u(r['tc_ang']) * rad)
    return pmu, ti_v, ti_i


def bayes(F, d, W, alpha, K, idx):
    """Média a posteriori de θ com W pontos de operação empilhados e MAPE mínimo teórico (gaussiano).

    Erro de cada canal X (V1, V2, I1, por fase): δX ≈ X(ε_m + j ε_a). O resíduo da equação da linha é
    δΔV − ℓ Z δI, com Z na média a priori. A parte da µPMU é independente entre pontos de operação; a dos
    TIs é a mesma nos W pontos e entra na covariância como um termo comum."""
    Ytr = d['Y'][d['idx_tr']]
    mu, Sig = Ytr.mean(0), np.diag(Ytr.var(0))
    Z0 = fl.matriz_Z(mu[None])[0]
    pmu, ti_v, ti_i = _desvios(alpha, K) if alpha > 0 else (None, None, None)
    med, sd = np.empty((len(idx), 12)), np.empty((len(idx), 12))
    for m, i in enumerate(idx):
        V1, V2, I1 = F['V1'][i, :W], F['V2'][i, :W], F['I1'][i, :W]
        Is = I1 - V1 @ d['Y_meio'].T
        J = np.vstack([fl.jacobiano(Is[k], d['ell']) for k in range(W)])
        dV = V1 - V2
        y = np.concatenate([np.r_[v.real, v.imag] for v in dV])
        R = np.zeros((6 * W, 6 * W))
        if alpha > 0:
            # A: (6W × 18) mapeia [ε_m, ε_a] de V1, V2, I1 (3 fases cada) no resíduo [Re; Im] de cada ponto
            A = np.zeros((6 * W, 18))
            for k in range(W):
                for p in range(3):
                    for col, z in ((p, V1[k, p]), (3 + p, -V2[k, p])):
                        A[6 * k + p, 2 * col], A[6 * k + p, 2 * col + 1] = z.real, -z.imag
                        A[6 * k + 3 + p, 2 * col], A[6 * k + 3 + p, 2 * col + 1] = z.imag, z.real
                    for q in range(3):
                        z = -d['ell'] * Z0[p, q] * Is[k, q]
                        col = 6 + q
                        A[6 * k + p, 2 * col] += z.real
                        A[6 * k + p, 2 * col + 1] += -z.imag
                        A[6 * k + 3 + p, 2 * col] += z.imag
                        A[6 * k + 3 + p, 2 * col + 1] += z.real
            s_ti = np.array([ti_v['m'], ti_v['a']] * 6 + [ti_i['m'], ti_i['a']] * 3) ** 2
            s_pmu = np.array([pmu['m'], pmu['a']] * 9) ** 2
            R = A @ np.diag(s_ti) @ A.T
            for k in range(W):
                Ak = A[6 * k:6 * k + 6]
                R[6 * k:6 * k + 6, 6 * k:6 * k + 6] += Ak @ np.diag(s_pmu) @ Ak.T
        S = J @ Sig @ J.T + R + 1e-12 * np.eye(6 * W)
        G = Sig @ J.T @ np.linalg.inv(S)
        med[m] = mu + G @ (y - J @ mu)
        sd[m] = np.sqrt(np.clip(np.diag(Sig - G @ J @ Sig), 0, None))
    Yte = d['Y'][idx]
    return fl.mape(Yte, med), 100 * math.sqrt(2 / math.pi) * np.mean(sd / np.abs(Yte), axis=0)


# ---------------------------------------------------------------- experimento
def experimento(d, W, config='both', alpha=0.0, K=1, rapido=False, referencia=True, log=print):
    """MAPE (%) por parâmetro no teste para cada modelo (+ média do treino e referência da linha)."""
    F = com_ruido(d, alpha, K)
    X = entradas(F, W, config)
    Y, itr, ite = d['Y'], d['idx_tr'], d['idx_te']
    keep = X[itr].std(0) > 0
    sx, sy = StandardScaler().fit(X[itr][:, keep]), StandardScaler().fit(Y[itr])
    Xtr, Xte = sx.transform(X[itr][:, keep]), sx.transform(X[ite][:, keep])
    out = {'Prior mean': fl.mape(Y[ite], np.broadcast_to(Y[itr].mean(0), Y[ite].shape))}
    for nome, m in fl.novos_modelos(rapido).items():
        t0 = time.time()
        m.fit(Xtr, sy.transform(Y[itr]))
        out[nome] = fl.mape(Y[ite], sy.inverse_transform(m.predict(Xte)))
        log(f'    {nome:12s} {out[nome].mean():.4f} %  ({time.time() - t0:.0f} s)')
        del m
        gc.collect()
    if referencia and config == 'both':
        out['Line-equation Bayes'], out['Line-equation bound'] = bayes(F, d, W, alpha, K, ite)
    return pd.DataFrame(out, index=g.PARAMS)
