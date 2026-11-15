# EstimacaoFeeder

Estimação *model-free*, por aprendizado de máquina, da matriz de impedância série trifásica de um trecho de alimentador de distribuição a partir de medições de micro-PMUs (µPMUs) nos terminais do trecho.

O repositório contém os dados e os notebooks do artigo *Model-Free Machine-Learning Estimation of Three-Phase Feeder Impedance Parameters from µPMU Measurements under Realistic Instrument Uncertainty* (em preparação).

---

## Problema

Um trecho trifásico de comprimento ℓ, sem cargas intermediárias, obedece a

ΔV = V_s − V_r = ℓ · Z · I,

em que **Z** é a matriz de impedância série 3×3, simétrica. Ela tem seis entradas complexas distintas, ou seja, 12 parâmetros reais:

θ = [r11, r12, r22, r13, r23, r33, x11, x12, x22, x13, x23, x33]

O objetivo é estimar θ diretamente das medições das µPMUs, sem usar a equação da linha, o comprimento ℓ ou a topologia da rede. Em cada terminal, a µPMU mede o módulo e o ângulo das tensões e correntes das três fases, e as potências por fase são calculadas a partir delas. Três configurações são avaliadas: µPMUs nos dois terminais, só no terminal emissor e só no receptor.

---

## Estudos de caso

| | IEEE 13 barras | Alimentador do Belvedere (Cuiabá) |
|---|---|---|
| Trecho | RG60 → 632 (2000 ft) | primeiro trecho do tronco (≈ 7,1 m) |
| Origem | IEEE 13-bus test feeder | BDGD da distribuidora + OpenDSS |
| Tensão nominal | 4,16 kV | 13,8 kV |
| Perturbação dos parâmetros | 1 % | 1 % a 29 % |
| Vetores de parâmetros por nível | 10 000 | 10 000 |
| Pontos de operação por vetor | 5 (cargas variando ±30 %) | 1 (carga fixa) |

Em cada amostra, os 12 parâmetros são perturbados de forma independente (gaussiana, com desvio-padrão relativo igual ao nível).

- **Belvedere:** o fluxo de potência é resolvido com a carga fixa.
- **IEEE 13 barras:** só o trecho 650632 recebe os parâmetros perturbados. Cada vetor é resolvido em 5 pontos de operação, com cada uma das 15 cargas multiplicada por um fator independente U(0,7; 1,3) e os reguladores ativos. Isso muda o desequilíbrio, de modo que as correntes dos 5 pontos são linearmente independentes, condição do Corolário 2 para identificar os 12 parâmetros (50 000 fluxos de potência).

---

## Modelo de ruído de medição

Segue D'Antona et al., *IEEE Trans. Instrum. Meas.*, 2026:

| Fonte | Módulo | Ângulo | Comportamento |
|---|---|---|---|
| µPMU | ±0,2 % | ±0,2 crad | aleatório, novo sorteio a cada amostra |
| TP classe 1 | ±1 % | ±1,2 crad | sistemático, fixo por canal |
| TC classe 1 | ±1 % | ±1,8 crad | sistemático, fixo por canal |

Todos os erros são uniformes. O nível de ruído é controlado por um fator de escala α e pelo número K de amostras sincronizadas do mesmo ponto de operação cuja média é usada. Treino e teste usam a mesma realização dos erros dos TIs, que também é a mesma nos 5 pontos de operação de uma amostra.

---

## Estrutura do repositório

```text
EstimacaoFeeder/
├── Dados13barras/                          # IEEE 13 barras
│   ├── snapshots/                          # base atual: 5 pontos de operação por vetor de parâmetros
│   │   ├── dss/                            # arquivos do circuito (OpenDSS)
│   │   ├── gerador_snapshots.py            # gera a base (opendssdirect)
│   │   ├── Gera_Snapshots.ipynb            # geração e verificação do Teorema 2
│   │   ├── snapshots_0.01_K5.csv.gz        # base: 10 000 vetores × 5 pontos de operação
│   │   ├── snaplib.py                      # ruído, entradas, modelos e referência pela equação da linha
│   │   ├── run_ieee13_snapshots.py         # experimentos do paper → resultados_ieee13_snapshots.pkl
│   │   └── Estima_Snapshots.ipynb          # comparação 1 × 5 pontos de operação, com e sem ruído
│   ├── resultados_completos_0.01.csv       # dataset antigo sem ruído (1 ponto de operação, linecode mtx601)
│   ├── resultados_completos_com_ruido.csv  # dataset antigo com ruído (gerado por ComRuido.ipynb)
│   └── erros_sistematicos_TI_seed1.csv     # erros sistemáticos sorteados para os TIs
├── DadosBelvedere/                         # alimentador real do Belvedere
│   ├── 0_0_09_resultados_perturbacoes_potencia.xlsx    # abas pert_0.01 a pert_0.09
│   ├── 0_1_0_19_resultados_perturbacoes_potencia.xlsx  # abas pert_0.10 a pert_0.19
│   ├── 0_2_0_29_resultados_perturbacoes_potencia.xlsx  # abas pert_0.20 a pert_0.29
│   ├── feederlib.py                # dados, ruído, modelos, estimador bayesiano e limite teórico
│   ├── Estima_Belvedere.ipynb      # experimentos E1, E2 e E3
│   ├── resultados_belvedere.pkl    # resultados salvos dos experimentos
│   └── figuras/                    # figuras em PDF geradas pelo notebook
├── Paper/
│   ├── gera_figuras_tabelas.py     # figuras e tabelas do artigo a partir dos .pkl
│   ├── figures/                    # figuras (PDF)
│   └── tables/                     # tabelas (LaTeX)
├── ComRuido.ipynb                  # IEEE 13: adiciona o ruído de medição ao dataset
├── Estima.ipynb                    # IEEE 13: estimação com dados sem ruído
├── Estima_Ruido.ipynb              # IEEE 13: estimação com dados com ruído
└── README.md
```

A aba `pert_0` das planilhas do Belvedere não tem variação dos parâmetros e não é usada.

---

## Notebooks

**IEEE 13 barras, base atual** (`Dados13barras/snapshots/`)
- `Gera_Snapshots.ipynb`: gera a base com `gerador_snapshots.py` e confirma o Teorema 2 (dimensão não observável 6, 2 e 0 com 1, 2 e 3 pontos de operação).
- `run_ieee13_snapshots.py`: roda os experimentos do artigo com W = 1 e W = 5 pontos de operação por amostra (posição das µPMUs, ruído com α ∈ {1; 0,1; 0,01} e K ∈ {1; 10; 100}). Leva cerca de 50 minutos e pode ser interrompido, porque os resultados vão sendo salvos.
- `Estima_Snapshots.ipynb`: comparação direta entre 1 e 5 pontos de operação, com e sem ruído, incluindo um teste com entradas físicas (ΔV, corrente série e estimativas pela equação da linha).

**IEEE 13 barras, dataset antigo** (um ponto de operação, perturbação no linecode mtx601 inteiro)
- `Estima.ipynb`: estimação com os dados sem ruído.
- `ComRuido.ipynb`: aplica o modelo de ruído (µPMU + TI) e gera `resultados_completos_com_ruido.csv`. A semente `IT_SEED` define a realização dos erros dos TIs.
- `Estima_Ruido.ipynb`: compara os modelos com e sem ruído.

**Belvedere** (`DadosBelvedere/Estima_Belvedere.ipynb`)
- **E1, posição das µPMUs:** dois terminais, só o emissor e só o receptor; dados sem ruído e perturbação de 1 %.
- **E2, nível de perturbação:** de 1 % a 29 %, sem ruído.
- **E3, ruído de µPMU + TI:** α ∈ {1; 0,1; 0,01} e K ∈ {1; 10; 100}, com perturbações de 1 %, 9 % e 29 %.

Os modelos são Ridge, MLP, LightGBM e Random Forest. As referências são a média dos parâmetros de treino (equivale a não estimar nada; MAPE ≈ 0,8 × perturbação) e o estimador bayesiano baseado na equação da linha, junto com o limite teórico de MAPE correspondente. Com W pontos de operação, as W equações da linha são empilhadas. A métrica é o MAPE por parâmetro no conjunto de teste (divisão 80/20 por vetor de parâmetros).

O notebook carrega os resultados de `resultados_belvedere.pkl`. Para refazer todos os experimentos (cerca de 20 minutos), use `RECALCULAR = True`.

---

## Principais resultados

Perturbação de 1 %: devolver a média do treino, sem estimar nada, dá MAPE de 0,80 %.

- **Sem ruído:** o Ridge chega a 0,53 % nos dois trechos. Com um único ponto de operação, isso coincide com o estimador ótimo pela equação da linha: só seis combinações dos 12 parâmetros são identificáveis. As reatâncias são bem estimadas, as resistências próprias em parte e as mútuas não.
- **Janela de 5 pontos de operação (IEEE 13):** os 12 parâmetros ficam identificáveis, e o estimador pela equação da linha empilhada os recupera quase exatamente (0,0004 %). Os modelos de ML com as medições brutas não aproveitam a janela e continuam em 0,53 %.
- **Posição das µPMUs:** uma µPMU só no terminal receptor mantém a maior parte da informação (0,63 % no IEEE 13 e 0,53 % no Belvedere). Só no emissor, o IEEE 13 fica na média.
- **Com ruído nominal (TIs classe 1):** o estimador pela equação da linha fica na média. O Ridge, treinado e testado com os mesmos TIs, chega a 0,68 % com 5 pontos de operação e 0,75 % com 1. O que limita a estimação é a razão sinal-ruído da queda de tensão no trecho.
- **Belvedere:** o trecho de 7 m tem queda de tensão de cerca de 10⁻⁴ pu e é inobservável com µPMUs e TIs reais.

---

## Execução

```bash
git clone https://github.com/FProencadeAlbuquerque/EstimacaoFeeder.git
cd EstimacaoFeeder
pip install numpy pandas scipy scikit-learn lightgbm matplotlib openpyxl jupyter opendssdirect.py
jupyter notebook
```

Para refazer os resultados do IEEE 13 barras e as figuras e tabelas do artigo:

```bash
cd Dados13barras/snapshots && python run_ieee13_snapshots.py
cd ../../Paper && python gera_figuras_tabelas.py
```

Os notebooks do Belvedere devem ser executados de dentro da pasta `DadosBelvedere`, porque leem as planilhas e a `feederlib.py` da própria pasta.

---

## Autores

- Felipe Proença de Albuquerque (UFMT)
- Cássio Gerez
- Camila dos Anjos Fantin (UFMT)
- Eduardo Coelho Marques da Costa (USP)
- Raoni Florentino da Silva Teixeira (UFMT)
