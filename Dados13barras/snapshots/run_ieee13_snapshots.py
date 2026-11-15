"""Gera resultados_ieee13_snapshots.pkl com todos os experimentos do IEEE 13 barras usados no paper.

Chaves: ('E1', W, config) sem ruído; ('E3', W, alpha, K) com µPMUs nos dois terminais;
('E4', W, config, alpha, K) para µPMU só em um terminal. W = pontos de operação por θ (1 ou 5).
Pode ser interrompido: os resultados já calculados ficam no pkl e não são refeitos.
"""
import pickle, time
from pathlib import Path
import snaplib as s

PKL = Path(__file__).resolve().parent / 'resultados_ieee13_snapshots.pkl'
R = pickle.load(open(PKL, 'rb')) if PKL.exists() else {}
d = s.carregar()


def run(chave, **kw):
    if chave in R:
        return
    t0 = time.time()
    print(chave, flush=True)
    R[chave] = s.experimento(d, log=lambda m: print(m, flush=True), **kw)
    pickle.dump(R, open(PKL, 'wb'))
    print(f'  -> média {R[chave].mean().round(4).to_dict()}  ({time.time() - t0:.0f} s)', flush=True)


for W in (5, 1):
    for cfg in (('both', 'sending', 'receiving') if W == 5 else ('both',)):
        run(('E1', W, cfg), W=W, config=cfg)
for W in (1, 5):
    for a in (1.0, 0.1, 0.01):
        for K in (1, 10, 100):
            run(('E3', W, a, K), W=W, config='both', alpha=a, K=K, rapido=True)
    for cfg in ('sending', 'receiving'):
        for a, K in [(0.1, 1), (1.0, 100)]:
            run(('E4', W, cfg, a, K), W=W, config=cfg, alpha=a, K=K, rapido=True)
print('fim')
