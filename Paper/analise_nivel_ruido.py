"""MAPE em função do nível de ruído (fator α sobre os erros de µPMU e TI; α = 1 é o nominal, TIs classe 1).

Ridge e referência pela equação da linha, K = 1, µPMUs nos dois terminais.
IEEE 13 barras e alimentador de Cuiabá, cada um com W = 1 e W = 5 pontos de operação por amostra.
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
NOMES = {'ieee13': 'IEEE 13-bus', 'cuiaba': 'Cuiabá feeder'}
CASOS = [f'{NOMES[c]}, W = {W}' for c in NOMES for W in (1, 5)]

if PKL.exists():
    R = pickle.load(open(PKL, 'rb'))
else:
    R = {}
    fl.novos_modelos = lambda rapido=False: {'Ridge': Ridge(alpha=1e-3)}
    for c, nome in NOMES.items():
        d = sl.carregar(c)
        for a in (ALPHAS_CU if c == 'cuiaba' else []) + ALPHAS:
            for W in (1, 5):
                R[(f'{nome}, W = {W}', a)] = sl.experimento(d, W, 'both', a, 1, log=lambda m: None)
            print(nome, a, {k[0]: round(v['Ridge'].mean(), 3) for k, v in R.items() if k[1] == a}, flush=True)
    pickle.dump(R, open(PKL, 'wb'))

COLS = ['Ridge', 'Line-equation Bayes', 'Line-equation bound']
serie = lambda c: sorted(a for (cc, a) in R if cc == c and a > 0)
T = {c: pd.DataFrame({m: [R[(c, a)][m].mean() for a in [0.0] + serie(c)] for m in COLS}, index=[0.0] + serie(c))
     for c in CASOS}
G = {c: pd.DataFrame({g: [R[(c, a)].loc[ps, 'Ridge'].mean() for a in [0.0] + serie(c)] for g, ps in fl.GRUPOS.items()},
                     index=[0.0] + serie(c)) for c in CASOS}
for c in CASOS:
    print(c); print(pd.concat([T[c], G[c]], axis=1).round(3).to_string())

# tabela (mesmos α nos quatro casos)
rot = lambda a: 'noise-free' if a == 0 else f'{a:g}'
linhas = [' & '.join([rot(a), '--' if a == 0 else f'{a:g}'] + [f'{T[c].loc[a, m]:.3f}' for c in CASOS
                                                              for m in ('Ridge', 'Line-equation bound')]) + ' \\\\'
          for a in ALPHAS]
cab = ' & '.join(f'\\multicolumn{{2}}{{c}}{{{c.split(",")[0]}, $W={c[-1]}$}}' for c in CASOS)
tex = ['\\begin{table}[htbp]', '\\centering', '\\small',
       '\\caption{Mean MAPE (\\%) versus the measurement-noise level ($K=1$, $\\mu$PMUs at both terminals). '
       'The noise scale $\\alpha$ multiplies all $\\mu$PMU and IT error bounds; the IT ratio error is $\\pm\\alpha$\\,\\%. '
       'Training and test share the same realization of the systematic IT errors.}',
       '\\label{tab:e5}', '\\resizebox{\\linewidth}{!}{%', '\\begin{tabular}{ll' + 'r' * 8 + '}', '\\toprule',
       ' &  & ' + cab + ' \\\\',
       ''.join(f'\\cmidrule(lr){{{3 + 2 * k}-{4 + 2 * k}}}' for k in range(4)),
       '$\\alpha$ & IT ratio error (\\%) & ' + ' & '.join(['Ridge & Bound'] * 4) + ' \\\\', '\\midrule'] + linhas + \
      ['\\bottomrule', '\\end{tabular}', '}', '\\end{table}']
(AQUI / 'tables' / 'E5_noise_level.tex').write_text('\n'.join(tex) + '\n')

# figura
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.3,
                     'font.size': 11, 'axes.titlesize': 11, 'pdf.fonttype': 42})
COR = {'Reactances': '#2a78d6', 'Self resistances': '#1baf7a', 'Mutual resistances': '#eb6834'}
fig, axs = plt.subplots(2, 2, figsize=(7.2, 7.4), sharey=True)
for ax, c in zip(axs.ravel(), CASOS):
    Tc, Gc = T[c].drop(0.0), G[c].drop(0.0)
    ax.plot(Tc.index, Tc['Ridge'], 'k-o', lw=2.2, ms=5, label='Ridge, all 12 parameters')
    ax.plot(Tc.index, Tc['Line-equation bound'], '--s', color='#8a8984', ms=5, lw=1.6, label='Line-equation bound')
    for g in fl.GRUPOS:
        ax.plot(Gc.index, Gc[g], '-', color=COR[g], lw=1.5, marker='.', ms=7, label=f'Ridge, {g.lower()}')
    ax.axhline(T[c].loc[0.0, 'Ridge'], color='k', ls='-.', lw=0.9, label='Ridge, noise-free')
    ax.axvline(1.0, color='#52514e', ls=':', lw=1)
    ax.set_xscale('log'); ax.set_title(c.replace('W = ', '$W=') + '$')
    ax.set_xlabel('noise scale α  (IT ratio error = ±α %)'); ax.tick_params(labelleft=True)
for ax in axs[:, 0]:
    ax.set_ylabel('mean MAPE (%)')
axs[0, 0].set_ylim(0, None)
axs[0, 0].text(1.0, 0.02, ' class-1 ITs', rotation=90, va='bottom', ha='right', fontsize=9, color='#52514e')
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, frameon=False, fontsize=10)
plt.tight_layout(rect=(0, 0.12, 1, 1)); plt.savefig(AQUI / 'figures' / 'E5_noise_level.pdf', bbox_inches='tight')
