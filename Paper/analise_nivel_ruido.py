"""MAPE em função do nível de ruído (fator α sobre os erros de µPMU e TI; α = 1 é o nominal, TIs classe 1).

Ridge e referência pela equação da linha, K = 1, µPMUs nos dois terminais, espalhamento de 1 %.
IEEE 13 barras com W = 1 e W = 5 pontos de operação; alimentador de Cuiabá com 1 ponto.
Saídas: resultados_nivel_ruido.pkl, figures/E5_noise_level.pdf, tables/E5_noise_level.tex
"""
import pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

AQUI = Path(__file__).resolve().parent; RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / 'DadosBelvedere')); sys.path.insert(0, str(RAIZ / 'Dados13barras' / 'snapshots'))
import feederlib as fl, snaplib as sl
from sklearn.linear_model import Ridge

ALPHAS = [0.0, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
ALPHAS_CU = [1e-4, 3e-4, 1e-3, 3e-3]          # níveis extras só para o trecho curto de Cuiabá
PKL = AQUI / 'resultados_nivel_ruido.pkl'
so_ridge = lambda rapido=False: {'Ridge': Ridge(alpha=1e-3)}

if PKL.exists():
    R = pickle.load(open(PKL, 'rb'))
else:
    R = {}
    fl.novos_modelos = so_ridge
    ie, cu = sl.carregar(), fl.carregar(0.01, RAIZ / 'DadosBelvedere')
    for a in ALPHAS:
        for W in (1, 5):
            R[(f'IEEE 13-bus, W = {W}', a)] = sl.experimento(ie, W, 'both', a, 1, log=lambda m: None)
        R[('Cuiabá feeder', a)] = fl.experimento(cu, 'both', a, 1, modelos=so_ridge(), it_seeds_teste=())[0]
        print(a, {k[0]: v.mean().round(3).to_dict() for k, v in R.items() if k[1] == a}, flush=True)
    for a in ALPHAS_CU:
        R[('Cuiabá feeder', a)] = fl.experimento(cu, 'both', a, 1, modelos=so_ridge(), it_seeds_teste=())[0]
    pickle.dump(R, open(PKL, 'wb'))

CASOS = ['IEEE 13-bus, W = 1', 'IEEE 13-bus, W = 5', 'Cuiabá feeder']
COLS = ['Ridge', 'Line-equation Bayes', 'Line-equation bound']
T = pd.DataFrame({(c, m): [R[(c, a)][m].mean() for a in ALPHAS] for c in CASOS for m in COLS}, index=ALPHAS)
print(T.round(3).to_string())
G = pd.DataFrame({(c, g): [R[(c, a)].loc[ps, 'Ridge'].mean() for a in ALPHAS]
                  for c in CASOS for g, ps in fl.GRUPOS.items()}, index=ALPHAS)
print(G.round(3).to_string())
TC = pd.DataFrame({m: [R[('Cuiabá feeder', a)][m].mean() for a in ALPHAS_CU] for m in COLS}, index=ALPHAS_CU)
GC = pd.DataFrame({g: [R[('Cuiabá feeder', a)].loc[ps, 'Ridge'].mean() for a in ALPHAS_CU]
                   for g, ps in fl.GRUPOS.items()}, index=ALPHAS_CU)
print(TC.round(3).to_string())

# tabela
rot = lambda a: 'noise-free' if a == 0 else f'{a:g}'
linhas = [' & '.join([rot(a), '--' if a == 0 else f'{a:g}'] + [f'{T.loc[a, (c, m)]:.3f}' for c in CASOS for m in ('Ridge', 'Line-equation bound')]) + ' \\\\'
          for a in ALPHAS]
tex = ['\\begin{table}[htbp]', '\\centering', '\\small',
       '\\caption{Mean MAPE (\\%) versus the measurement-noise level ($K=1$, $\\mu$PMUs at both terminals, 1\\% parameter '
       'spread). The noise scale $\\alpha$ multiplies all $\\mu$PMU and IT error bounds; the IT ratio error is $\\pm\\alpha$\\,\\%. '
       'Training and test share the same realization of the systematic IT errors.}',
       '\\label{tab:e5}', '\\begin{tabular}{llrrrrrr}', '\\toprule',
       ' &  & \\multicolumn{2}{c}{IEEE 13-bus, $W=1$} & \\multicolumn{2}{c}{IEEE 13-bus, $W=5$} & \\multicolumn{2}{c}{Cuiabá feeder} \\\\',
       '\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}',
       '$\\alpha$ & IT ratio error (\\%) & ' + ' & '.join(['Ridge & Bound'] * 3) + ' \\\\', '\\midrule'] + linhas + \
      ['\\bottomrule', '\\end{tabular}', '\\end{table}']
(AQUI / 'tables' / 'E5_noise_level.tex').write_text('\n'.join(tex) + '\n')

# figura
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3,
                     'font.size': 10, 'pdf.fonttype': 42})
A = ALPHAS[1:]
fig, axs = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
COR = {'Reactances': '#2a78d6', 'Self resistances': '#1baf7a', 'Mutual resistances': '#eb6834'}
for ax, c in zip(axs, CASOS):
    Tc, Gc = T[c].loc[A], G[c].loc[A]
    if c.startswith('Cuiabá'):
        Tc, Gc = pd.concat([TC, Tc]), pd.concat([GC, Gc])
    ax.plot(Tc.index, Tc['Ridge'], 'k-o', lw=2, ms=4, label='Ridge, all 12 parameters')
    ax.plot(Tc.index, Tc['Line-equation bound'], '--s', color='#8a8984', ms=4, label='Line-equation bound')
    for g in fl.GRUPOS:
        ax.plot(Gc.index, Gc[g], '-', color=COR[g], lw=1.2, marker='.', label=f'Ridge, {g.lower()}')
    ax.axhline(T.loc[0.0, (c, 'Ridge')], color='k', ls='-.', lw=0.9, label='Ridge, noise-free')
    ax.axvline(1.0, color='#52514e', ls=':', lw=1)
    ax.set_xscale('log'); ax.set_title(c); ax.set_xlabel('noise scale α  (IT ratio error = ±α %)')
axs[0].set_ylabel('mean MAPE (%)'); axs[0].set_ylim(0, None)
axs[0].text(1.0, 0.02, ' class-1 ITs', rotation=90, va='bottom', ha='right', fontsize=8, color='#52514e')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=6, frameon=False, fontsize=8)
plt.tight_layout(rect=(0, 0.07, 1, 1)); plt.savefig(AQUI / 'figures' / 'E5_noise_level.pdf', bbox_inches='tight')
