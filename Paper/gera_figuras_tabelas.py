"""Gera as figuras (PDF) e as tabelas (LaTeX) do paper.

Entradas:
  ../Dados13barras/snapshots/resultados_ieee13_snapshots.pkl (run_ieee13_snapshots.py)
  ../DadosBelvedere/resultados_cuiaba_snapshots.pkl          (run_cuiaba_snapshots.py)
Saídas: figures/*.pdf e tables/*.tex nesta pasta, além dos números citados no texto (impressos).

Nos dois alimentadores, cada amostra tem W pontos de operação (W = 1 ou 5) do mesmo θ.
Em todos os casos com ruído, treino e teste usam a mesma realização dos erros dos TIs.
"""
import os
import sys
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / 'DadosBelvedere'))
sys.path.insert(0, str(RAIZ / 'Dados13barras' / 'snapshots'))
import feederlib as fl            # noqa: E402
import snaplib as sl              # noqa: E402
from feederlib import PARAMS, GRUPOS  # noqa: E402

FIG, TAB = AQUI / 'figures', AQUI / 'tables'
FIG.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.alpha': 0.3, 'font.size': 11, 'axes.titlesize': 11, 'lines.linewidth': 1.8, 'lines.markersize': 6, 'pdf.fonttype': 42})
COR = {'Ridge': '#2a78d6', 'MLP': '#eb6834', 'LightGBM': '#1baf7a', 'RandomForest': '#eda100',
       'Line-equation Bayes': '#6250d6', 'Line-equation bound': '#8a8984', 'Prior mean': '#52514e'}
MODELOS = ['Ridge', 'MLP', 'LightGBM', 'RandomForest']
REFS = ['Line-equation Bayes', 'Line-equation bound']
ALPHAS, KS = [1.0, 0.1, 0.01], [1, 10, 100]
W = 5                              # pontos de operação por amostra

RES = {'IEEE 13-bus': pickle.load(open(RAIZ / 'Dados13barras' / 'snapshots' / 'resultados_ieee13_snapshots.pkl', 'rb')),
       'Cuiabá feeder': pickle.load(open(RAIZ / 'DadosBelvedere' / 'resultados_cuiaba_snapshots.pkl', 'rb'))}
DADOS = {'IEEE 13-bus': sl.carregar('ieee13'), 'Cuiabá feeder': sl.carregar('cuiaba')}
CHAVE = {'IEEE 13-bus': 'ieee13', 'Cuiabá feeder': 'cuiaba'}
E1 = {case: {c: R[('E1', W, c)] for c in fl.CONFIGS} for case, R in RES.items()}


def grupos(tab):
    g = pd.DataFrame({k: tab.loc[v].mean() for k, v in GRUPOS.items()}).T
    g.loc['All 12 parameters'] = tab.mean()
    return g


# ------------------------------------------------------------------ LaTeX
def tex_table(header, rows, caption, label, align, midrules=(), resize=True):
    s = ['\\begin{table}[htbp]', '\\centering', '\\small', f'\\caption{{{caption}}}', f'\\label{{{label}}}',
         '\\resizebox{\\linewidth}{!}{%' if resize else '', f'\\begin{{tabular}}{{{align}}}', '\\toprule'] + header + ['\\midrule']
    for i, r in enumerate(rows):
        if i in midrules:
            s.append('\\midrule')
        s.append(' & '.join(r) + ' \\\\')
    s += ['\\bottomrule', '\\end{tabular}', '}' if resize else '', '\\end{table}']
    return '\n'.join(l for l in s if l) + '\n'


f3 = lambda x: f'{x:.3f}'
fx = lambda x: f'{x:.3f}' if x < 10 else (f'{x:.2f}' if x < 100 else f'{x:.0f}')
TABS = {}

# E1: posição das µPMUs (grupos), W = 5 nos dois alimentadores
rows, n_ieee = [], None
for case, d in E1.items():
    for cfg, rot in fl.CONFIGS.items():
        g = grupos(d[cfg])
        ordem = MODELOS + (REFS if cfg == 'both' else [])
        for m in [c for c in ordem if c in g.columns]:
            rows.append([case, rot.replace('µ', '$\\mu$'), m] + [f3(v) for v in g[m]])
    if n_ieee is None:
        n_ieee = len(rows)
TABS['E1_placement'] = tex_table(
    [' &  &  & Reactances & Self resistances & Mutual resistances & All 12 parameters \\\\',
     'case & $\\mu$PMU placement & model &  &  &  &  \\\\'], rows,
    'Mean MAPE (\\%) per parameter group for each $\\mu$PMU placement (noise-free data, '
    f'$W={W}$ operating points per sample).',
    'tab:e1', 'lllrrrr', midrules=(n_ieee,))

for case, key in CHAVE.items():
    t = E1[case]['both']
    cols = [c for c in MODELOS + REFS if c in t]
    TABS[f'E1_{key}_per_parameter'] = tex_table(
        [' & ' + ' & '.join(c for c in cols) + ' \\\\'],
        [[p] + [f3(t.loc[p, c]) for c in cols] for p in PARAMS],
        f'MAPE (\\%) per parameter, {case}, $\\mu$PMUs at both terminals, $W={W}$ operating points per sample, '
        'noise-free data.',
        f'tab:e1_{key}', 'l' + 'r' * len(cols))

# E3: ruído, W = 1 e W = 5
COLS3 = ['Ridge', 'MLP', 'LightGBM', 'Line-equation Bayes', 'Line-equation bound']
HEAD3 = [' &  & ' + ' & '.join(f'\\multicolumn{{2}}{{c}}{{{c}}}' for c in COLS3) + ' \\\\',
         ''.join(f'\\cmidrule(lr){{{3 + 2 * k}-{4 + 2 * k}}}' for k in range(5)),
         'noise scale & snapshots & ' + ' & '.join(['$W=1$ & $W=5$'] * 5) + ' \\\\']
for case, key in CHAVE.items():
    R = RES[case]
    rows = [['noise-free', '--'] + [f3(R[('E1', w, 'both')][c].mean()) for c in COLS3 for w in (1, W)]]
    for a in ALPHAS:
        for K in KS:
            rows.append([f'$\\alpha$ = {a:g}' if K == 1 else '', f'K = {K}']
                        + [fx(R[('E3', w, a, K)][c].mean()) for c in COLS3 for w in (1, W)])
    TABS[f'E3_noise_{key}'] = tex_table(
        HEAD3, rows,
        f'Mean MAPE (\\%) under $\\mu$PMU/IT measurement noise, {case}, with one ($W=1$) and five ($W=5$) '
        'operating points per sample. Training and test share the same realization of the systematic IT errors.',
        f'tab:e3_{key}', 'll' + 'r' * 10, midrules=(1, 4, 7))

# E4: posição com ruído
rows, mids = [], []
for case, R in RES.items():
    if rows:
        mids.append(len(rows))
    for cfg, rot in fl.CONFIGS.items():
        if cfg != 'both':
            mids.append(len(rows))
        for k, (a, K) in enumerate([(0.1, 1), (1.0, 100)]):
            get = (lambda w: R[('E3', w, a, K)]) if cfg == 'both' else (lambda w: R[('E4', w, cfg, a, K)])
            rows.append([case if (cfg == 'both' and k == 0) else '', rot.replace('µ', '$\\mu$') if k == 0 else '',
                         f'$\\alpha$ = {a:g}, K = {K}'] + [fx(get(w)[c].mean()) for c in COLS3[:3] for w in (1, W)])
TABS['E4_noise_placement'] = tex_table(
    [' &  &  & \\multicolumn{2}{c}{Ridge} & \\multicolumn{2}{c}{MLP} & \\multicolumn{2}{c}{LightGBM} \\\\',
     '\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}\\cmidrule(lr){8-9}',
     'case & $\\mu$PMU placement & noise & ' + ' & '.join(['$W=1$ & $W=5$'] * 3) + ' \\\\'],
    rows, 'Mean MAPE (\\%) with noisy measurements for each $\\mu$PMU placement, with one and '
          'five operating points per sample (same IT errors in training and test).',
    'tab:e4', 'lllrrrrrr', midrules=tuple(sorted(set(mids))))

for k, v in TABS.items():
    (TAB / f'{k}.tex').write_text(v)

# ------------------------------------------------------------------ figuras
fig, axs = plt.subplots(2, 1, figsize=(7, 6.6))
for ax, (case, d) in zip(axs, E1.items()):
    cfgs, w = list(fl.CONFIGS), 0.2
    for k, m in enumerate(MODELOS):
        ax.bar(np.arange(3) + (k - 1.5) * w, [d[c][m].mean() for c in cfgs], width=w - 0.02, color=COR[m], label=m)
    ax.axhline(d['both']['Line-equation bound'].mean(), color=COR['Line-equation bound'], ls='--', lw=1.2,
               label='Line-equation bound (both terminals)')
    ax.set_xticks(range(3), ['Both terminals', 'Sending end only', 'Receiving end only'])
    ax.set_ylabel('Mean MAPE (%)')
    ax.set_title(f'{case} ($W={W}$ operating points)')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=3, frameon=False, fontsize=10)
plt.tight_layout(rect=(0, 0.08, 1, 1)); plt.savefig(FIG / 'E1_placement.pdf', bbox_inches='tight'); plt.close()

fig, axs = plt.subplots(2, 1, figsize=(7.2, 7))
for ax, (case, d) in zip(axs, E1.items()):
    t, w = d['both'], 0.14
    for k, m in enumerate(MODELOS + REFS):
        ax.bar(np.arange(12) + (k - 2.5) * w, t[m], width=w - 0.02, color=COR[m], label=m)
    ax.set_xticks(range(12), PARAMS); ax.set_ylabel('MAPE (%)')
    ax.set_title(f'{case} — µPMUs at both terminals, $W={W}$ operating points')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=3, frameon=False, fontsize=10)
plt.tight_layout(rect=(0, 0.07, 1, 1)); plt.savefig(FIG / 'E1_per_parameter.pdf', bbox_inches='tight'); plt.close()


def snr(V1, dV_theta, a, K):
    """SNR do ΔV: dispersão de ΔV devida a θ (no ponto de operação) / erro da diferença de duas tensões."""
    sm, sav, _ = fl.sigmas(a, K)
    return np.sqrt(np.mean(np.abs(dV_theta) ** 2)) / (np.sqrt(2) * np.abs(V1).mean() * np.sqrt(sm ** 2 + sav ** 2))


def dV_theta(d):
    """Parte de ΔV causada pelo desvio de θ em relação à média, com a corrente de cada ponto de operação."""
    Is = d['I1'] - d['V1'] @ d['Y_meio'].T
    dZ = fl.matriz_Z(d['Y']) - fl.matriz_Z(d['Y'].mean(0)[None])[0]
    return d['ell'] * np.einsum('nij,npj->npi', dZ, Is)


SNR = {}
fig, axs = plt.subplots(2, 1, figsize=(7, 7.8))
for ax, (case, R) in zip(axs, RES.items()):
    d = DADOS[case]
    dvt = dV_theta(d)
    for K, mk in zip(KS, ['o', 's', '^']):
        xs = [snr(d['V1'], dvt, a, K) for a in ALPHAS]
        SNR[(case, K)] = xs
        ax.plot(xs, [R[('E3', W, a, K)]['Ridge'].mean() for a in ALPHAS], marker=mk, color=COR['Ridge'],
                label=f'Ridge, $W={W}$, K = {K}')
        ax.plot(xs, [R[('E3', 1, a, K)]['Ridge'].mean() for a in ALPHAS], marker=mk, ls=':',
                color=COR['MLP'], label=f'Ridge, $W=1$, K = {K}')
        ax.plot(xs, [R[('E3', W, a, K)]['Line-equation bound'].mean() for a in ALPHAS], marker=mk, ls='--',
                color=COR['Line-equation bound'], label=f'Line-equation bound, $W={W}$, K = {K}')
    ax.axhline(R[('E1', W, 'both')]['Ridge'].mean(), color='#52514e', lw=1, ls='-.', label=f'noise-free (Ridge, $W={W}$)')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('signal-to-noise ratio of ΔV'); ax.set_ylabel('mean MAPE (%)'); ax.set_title(case)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, frameon=False, fontsize=10)
plt.tight_layout(rect=(0, 0.17, 1, 1)); plt.savefig(FIG / 'E3_noise.pdf', bbox_inches='tight'); plt.close()

# ------------------------------------------------------------------ números citados no texto
for case, d in DADOS.items():
    Is = d['I1'] - d['V1'] @ d['Y_meio'].T
    dV = d['V1'] - d['V2']
    res = np.abs(dV - d['ell'] * np.einsum('nij,npj->npi', fl.matriz_Z(d['Y']), Is)).mean() / np.abs(dV).mean()
    sv = np.linalg.svd(np.swapaxes(Is, 1, 2), compute_uv=False)
    print(case, '|I| média e por fase:', np.abs(d['I1']).mean().round(0), np.abs(d['I1']).mean((0, 1)).round(0),
          ' |dV|/|V|:', f"{(np.abs(dV) / np.abs(d['V1'])).mean():.2e}", ' resíduo:', f'{res:.1e}',
          ' |I0|/|I|:', f"{(np.abs(d['I1'].sum(2)) / np.abs(d['I1']).mean(2)).mean():.1e}",
          ' σ3/σ1 (mediana):', f'{np.median(sv[:, 2] / sv[:, 0]):.1e}')
print('SNR:', {k: [f'{x:.2e}' for x in v] for k, v in SNR.items()})
print('ok')
