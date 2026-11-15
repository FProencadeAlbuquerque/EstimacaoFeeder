"""Gera as figuras (PDF) e as tabelas (LaTeX) do paper.

Entradas:
  ../DadosBelvedere/resultados_belvedere.pkl                (Estima_Belvedere.ipynb)
  ../Dados13barras/snapshots/resultados_ieee13_snapshots.pkl (run_ieee13_snapshots.py)
Saídas: figures/*.pdf e tables/*.tex nesta pasta, além dos números citados no texto (impressos).

IEEE 13 barras: cada amostra tem W pontos de operação (W = 1 ou 5) do mesmo θ.
Cuiabá (Belvedere): um único ponto de operação por amostra.
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
                     'axes.grid': True, 'grid.alpha': 0.3, 'font.size': 10, 'pdf.fonttype': 42})
COR = {'Ridge': '#2a78d6', 'MLP': '#eb6834', 'LightGBM': '#1baf7a', 'RandomForest': '#eda100',
       'Line-equation Bayes': '#6250d6', 'Line-equation bound': '#8a8984', 'Prior mean': '#52514e'}
MODELOS = ['Ridge', 'MLP', 'LightGBM', 'RandomForest']
REFS = ['Line-equation Bayes', 'Line-equation bound']
PRIOR = 'Prior mean'
ALPHAS, KS = [1.0, 0.1, 0.01], [1, 10, 100]
E2_MAX = 0.25
W = 5                              # pontos de operação por amostra no IEEE 13 barras

RB = pickle.load(open(RAIZ / 'DadosBelvedere' / 'resultados_belvedere.pkl', 'rb'))
RI = pickle.load(open(RAIZ / 'Dados13barras' / 'snapshots' / 'resultados_ieee13_snapshots.pkl', 'rb'))
ie = sl.carregar()
cu = {l: fl.carregar(l, RAIZ / 'DadosBelvedere') for l in (0.01, 0.09, 0.29)}


def prior_mape(Y):
    """MAPE de devolver a média do treino (mesma divisão 80/20 dos experimentos)."""
    from sklearn.model_selection import train_test_split
    itr, ite = train_test_split(np.arange(len(Y)), test_size=0.2, random_state=fl.SEED)
    return fl.mape(Y[ite], np.broadcast_to(Y[itr].mean(0), Y[ite].shape))


def com_prior(tab, Y):
    if PRIOR not in tab:
        tab = tab.copy()
        tab[PRIOR] = prior_mape(Y)
    return tab


E1 = {'IEEE 13-bus': {c: RI[('E1', W, c)] for c in fl.CONFIGS},
      'Cuiabá feeder': {c: com_prior(RB[('E1', c)], cu[0.01]['Y']) if c == 'both' else RB[('E1', c)]
                        for c in fl.CONFIGS}}


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
NOME = {PRIOR: 'Prior mean (no estimation)'}
TABS = {}

# E1: posição das µPMUs (grupos)
rows, n_ieee = [], None
for case, d in E1.items():
    for cfg, rot in fl.CONFIGS.items():
        g = grupos(d[cfg])
        ordem = ([PRIOR] if cfg == 'both' else []) + MODELOS + (REFS if cfg == 'both' else [])
        for m in [c for c in ordem if c in g.columns]:
            rows.append([case, rot.replace('µ', '$\\mu$'), NOME.get(m, m)] + [f3(v) for v in g[m]])
    if n_ieee is None:
        n_ieee = len(rows)
TABS['E1_placement'] = tex_table(
    [' &  &  & Reactances & Self resistances & Mutual resistances & All 12 parameters \\\\',
     'case & $\\mu$PMU placement & model &  &  &  &  \\\\'], rows,
    'Mean MAPE (\\%) per parameter group for each $\\mu$PMU placement (noise-free data, 1\\% parameter '
    f'spread). IEEE 13-bus: $W={W}$ operating points per sample; Cuiabá feeder: one operating point.',
    'tab:e1', 'lllrrrr', midrules=(n_ieee,))

for case, key in [('IEEE 13-bus', 'ieee13'), ('Cuiabá feeder', 'cuiaba')]:
    t = E1[case]['both']
    cols = [PRIOR] + [c for c in MODELOS + REFS if c in t]
    extra = f', $W={W}$ operating points per sample' if key == 'ieee13' else ''
    TABS[f'E1_{key}_per_parameter'] = tex_table(
        [' & ' + ' & '.join(NOME.get(c, c) for c in cols) + ' \\\\'],
        [[p] + [f3(t.loc[p, c]) for c in cols] for p in PARAMS],
        f'MAPE (\\%) per parameter, {case}, $\\mu$PMUs at both terminals{extra}, noise-free data.',
        f'tab:e1_{key}', 'l' + 'r' * len(cols))

# E2: espalhamento (Cuiabá, até 25 %)
niveis = [l for l in fl.NIVEIS if l <= E2_MAX + 1e-9]
e2 = pd.DataFrame({l: RB[('E2', l)].mean() for l in niveis}).T
cols2 = ['Ridge', 'MLP', 'LightGBM', 'Line-equation Bayes', 'Line-equation bound']
TABS['E2_spread'] = tex_table(
    [' & ' + ' & '.join(cols2) + ' \\\\', 'parameter spread &  &  &  &  &  \\\\'],
    [[f'{100 * l:g} \\%'] + [f3(e2.loc[l, c]) for c in cols2] for l in niveis],
    'Cuiabá feeder: mean MAPE (\\%) versus parameter spread (noise-free).', 'tab:e2', 'lrrrrr')

# E3: ruído
COLS3 = ['Ridge', 'MLP', 'LightGBM', 'Line-equation Bayes', 'Line-equation bound']
p_ieee = prior_mape(ie['Y']).mean()
HEAD3_IEEE = [' &  & ' + ' & '.join(f'\\multicolumn{{2}}{{c}}{{{c}}}' for c in COLS3) + ' \\\\',
              ''.join(f'\\cmidrule(lr){{{3 + 2 * k}-{4 + 2 * k}}}' for k in range(5)),
              'noise scale & snapshots & ' + ' & '.join(['$W=1$ & $W=5$'] * 5) + ' \\\\']
rows = [['noise-free', '--'] + [f3(RI[('E1', w, 'both')][c].mean()) for c in COLS3 for w in (1, W)]]
for a in ALPHAS:
    for K in KS:
        rows.append([f'$\\alpha$ = {a:g}' if K == 1 else '', f'K = {K}']
                    + [fx(RI[('E3', w, a, K)][c].mean()) for c in COLS3 for w in (1, W)])
TABS['E3_noise_ieee13'] = tex_table(
    HEAD3_IEEE, rows,
    'Mean MAPE (\\%) under $\\mu$PMU/IT measurement noise, IEEE 13-bus, with one ($W=1$) and five ($W=5$) '
    'operating points per sample. Training and test share the same realization of the systematic IT errors. '
    f'Returning the prior mean gives {p_ieee:.3f}\\,\\%.',
    'tab:e3_ieee13', 'll' + 'r' * 10, midrules=(1, 4, 7))

HEAD3 = [' &  & ' + ' & '.join(COLS3) + ' \\\\', 'noise scale & snapshots &  &  &  &  &  \\\\']
for lvl, key in [(0.01, 'cuiaba'), (0.09, 'cuiaba09'), (0.29, 'cuiaba29')]:
    clean = (RB[('E1', 'both')] if lvl == 0.01 else RB[('E2', lvl)]).mean()
    rows = [['noise-free', '--'] + [f3(clean[c]) for c in COLS3]]
    for a in ALPHAS:
        for K in KS:
            t = RB[('E3', lvl, a, K)].mean()
            rows.append([f'$\\alpha$ = {a:g}' if K == 1 else '', f'K = {K}'] + [fx(t[c]) for c in COLS3])
    pm = prior_mape(cu[lvl]['Y']).mean()
    TABS[f'E3_noise_{key}'] = tex_table(
        HEAD3, rows,
        f'Mean MAPE (\\%) under $\\mu$PMU/IT measurement noise, Cuiabá feeder ({100 * lvl:g}\\% spread). '
        f'Training and test share the same realization of the systematic IT errors. '
        f'Returning the prior mean gives {pm:.3f}\\,\\%.',
        f'tab:e3_{key}', 'llrrrrr', midrules=(1, 4, 7), resize=False)

# E4: IEEE 13, posição com ruído
rows = []
for cfg, rot in fl.CONFIGS.items():
    for k, (a, K) in enumerate([(0.1, 1), (1.0, 100)]):
        get = (lambda w: RI[('E3', w, a, K)]) if cfg == 'both' else (lambda w: RI[('E4', w, cfg, a, K)])
        rows.append([rot.replace('µ', '$\\mu$') if k == 0 else '', f'$\\alpha$ = {a:g}, K = {K}']
                    + [fx(get(w)[c].mean()) for c in COLS3[:3] for w in (1, W)])
TABS['E4_noise_placement'] = tex_table(
    [' &  & \\multicolumn{2}{c}{Ridge} & \\multicolumn{2}{c}{MLP} & \\multicolumn{2}{c}{LightGBM} \\\\',
     '\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}',
     '$\\mu$PMU placement & noise & ' + ' & '.join(['$W=1$ & $W=5$'] * 3) + ' \\\\'],
    rows, 'IEEE 13-bus: mean MAPE (\\%) with noisy measurements for each $\\mu$PMU placement, with one and '
          f'five operating points per sample (same IT errors in training and test; prior mean: {p_ieee:.3f}\\,\\%).',
    'tab:e4', 'llrrrrrr', midrules=(2, 4))

for k, v in TABS.items():
    (TAB / f'{k}.tex').write_text(v)

# ------------------------------------------------------------------ figuras
fig, axs = plt.subplots(1, 2, figsize=(13, 4))
for ax, (case, d) in zip(axs, E1.items()):
    cfgs, w = list(fl.CONFIGS), 0.2
    for k, m in enumerate(MODELOS):
        ax.bar(np.arange(3) + (k - 1.5) * w, [d[c][m].mean() for c in cfgs], width=w - 0.02, color=COR[m], label=m)
    ax.axhline(d['both'][PRIOR].mean(), color=COR[PRIOR], ls=':', lw=1.4, label='Prior mean (no estimation)')
    ax.axhline(d['both']['Line-equation bound'].mean(), color=COR['Line-equation bound'], ls='--', lw=1.2,
               label='Line-equation bound (both terminals)')
    ax.set_xticks(range(3), ['Both terminals', 'Sending end only', 'Receiving end only'])
    ax.set_ylabel('Mean MAPE (%)')
    ax.set_title(case + (f' ($W={W}$ operating points)' if case.startswith('IEEE') else ''))
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=6, frameon=False, fontsize=8)
plt.tight_layout(rect=(0, 0.07, 1, 1)); plt.savefig(FIG / 'E1_placement.pdf', bbox_inches='tight'); plt.close()

fig, axs = plt.subplots(2, 1, figsize=(12, 7))
for ax, (case, d) in zip(axs, E1.items()):
    t, w = d['both'], 0.12
    ms = [PRIOR] + MODELOS + REFS
    for k, m in enumerate(ms):
        ax.bar(np.arange(12) + (k - 3) * w, t[m], width=w - 0.02, color=COR[m], label=NOME.get(m, m))
    ax.set_xticks(range(12), PARAMS); ax.set_ylabel('MAPE (%)')
    extra = f', $W={W}$ operating points' if case.startswith('IEEE') else ''
    ax.set_title(f'{case} — µPMUs at both terminals, 1 % parameter spread{extra}')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=7, frameon=False, fontsize=8)
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(FIG / 'E1_per_parameter.pdf', bbox_inches='tight'); plt.close()

pct = np.array([100 * l for l in niveis])
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
for m in cols2:
    ls = '--' if m == 'Line-equation bound' else '-'
    axs[0].plot(pct, e2[m], ls=ls, marker='o', ms=3, color=COR[m], label=m)
    axs[1].plot(pct, e2[m] / pct, ls=ls, marker='o', ms=3, color=COR[m], label=m)
axs[0].set_xlabel('parameter spread (%)'); axs[0].set_ylabel('mean MAPE (%)'); axs[0].set_title('Cuiabá feeder — mean MAPE')
axs[1].set_xlabel('parameter spread (%)'); axs[1].set_ylabel('MAPE / spread'); axs[1].set_ylim(0, 0.8)
axs[1].set_title('Normalised by spread'); axs[1].legend(frameon=False, fontsize=8, loc='lower right')
plt.tight_layout(); plt.savefig(FIG / 'E2_spread.pdf', bbox_inches='tight'); plt.close()


def snr(V1, V2, dV_theta, a, K):
    """SNR do ΔV: dispersão de ΔV devida a θ (no ponto de operação) / erro da diferença de duas tensões."""
    sm, sav, _ = fl.sigmas(a, K)
    return np.sqrt(np.mean(np.abs(dV_theta) ** 2)) / (np.sqrt(2) * np.abs(V1).mean() * np.sqrt(sm ** 2 + sav ** 2))


def dV_theta_ieee(d):
    """Parte de ΔV causada pelo desvio de θ em relação à média, com a corrente de cada ponto de operação."""
    Is = d['I1'] - d['V1'] @ d['Y_meio'].T
    dZ = fl.matriz_Z(d['Y']) - fl.matriz_Z(d['Y'].mean(0)[None])[0]
    return sl.ELL * np.einsum('nij,npj->npi', dZ, Is)


dvt_ie = dV_theta_ieee(ie)
SNR = {}
fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
paineis = [('IEEE 13-bus, 1 % spread', (ie['V1'], ie['V2'], dvt_ie), True, RI[('E1', W, 'both')]),
           ('Cuiabá feeder, 1 % spread', cu[0.01], 0.01, RB[('E1', 'both')]),
           ('Cuiabá feeder, 9 % spread', cu[0.09], 0.09, RB[('E2', 0.09)])]
for ax, (nome, d, lvl, base) in zip(axs, paineis):
    ieee = lvl is True
    for K, mk in zip(KS, ['o', 's', '^']):
        if ieee:
            xs = [snr(d[0], d[1], d[2], a, K) for a in ALPHAS]
            get = lambda a, w=W: RI[('E3', w, a, K)]
        else:
            dV = d['V1'] - d['V2']
            xs = [snr(d['V1'], d['V2'], dV - dV.mean(0), a, K) for a in ALPHAS]
            get = lambda a, l=lvl: RB[('E3', l, a, K)]
        SNR[(nome, K)] = xs
        ax.plot(xs, [get(a)['Ridge'].mean() for a in ALPHAS], marker=mk, color=COR['Ridge'],
                label=f'Ridge, K = {K}' + (f' ($W={W}$ for IEEE 13)' if K == 1 else ''))
        if ieee:
            ax.plot(xs, [RI[('E3', 1, a, K)]['Ridge'].mean() for a in ALPHAS], marker=mk, ls=':',
                    color=COR['MLP'], label=f'Ridge, $W=1$, K = {K}')
        ax.plot(xs, [get(a)['Line-equation bound'].mean() for a in ALPHAS], marker=mk, ls='--',
                color=COR['Line-equation bound'], label=f'Line-equation bound, K = {K}')
    ax.axhline(base['Ridge'].mean(), color='#52514e', lw=1, ls='-.', label='noise-free (Ridge)')
    y_prior = (prior_mape(ie['Y']) if ieee else prior_mape(d['Y'])).mean()
    ax.axhline(y_prior, color='k', lw=1, ls=(0, (1, 2)), label='prior mean (no estimation)')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('signal-to-noise ratio of ΔV'); ax.set_ylabel('mean MAPE (%)'); ax.set_title(nome)
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=4, frameon=False, fontsize=8)
plt.tight_layout(rect=(0, 0.16, 1, 1)); plt.savefig(FIG / 'E3_noise.pdf', bbox_inches='tight'); plt.close()

# ------------------------------------------------------------------ números citados no texto
Is = ie['I1'] - ie['V1'] @ ie['Y_meio'].T
dV = ie['V1'] - ie['V2']
res = np.abs(dV - sl.ELL * np.einsum('nij,npj->npi', fl.matriz_Z(ie['Y']), Is)).mean() / np.abs(dV).mean()
print('IEEE13 |I| média e por fase:', np.abs(ie['I1']).mean().round(0), np.abs(ie['I1']).mean((0, 1)).round(0))
print('IEEE13 |dV| média:', np.abs(dV).mean().round(1), ' |dV|/|V|:', f"{(np.abs(dV) / np.abs(ie['V1'])).mean():.2e}",
      ' resíduo:', f'{res:.1e}')
print('IEEE13 prior:', round(p_ieee, 4), ' Cuiabá prior 1/9/29 %:',
      [round(prior_mape(cu[l]['Y']).mean(), 3) for l in (0.01, 0.09, 0.29)])
print('SNR:', {k: [f'{x:.2e}' for x in v] for k, v in SNR.items()})
print('E2 MAPE/spread:', (e2['Ridge'] / (100 * e2.index.values)).round(3).to_dict())
print('ok')
