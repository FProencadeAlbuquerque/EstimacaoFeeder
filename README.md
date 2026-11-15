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
| Amostras por nível | 10 000 | 10 000 |

Em cada amostra, os 12 parâmetros são perturbados de forma independente (gaussiana, com desvio-padrão relativo igual ao nível) e o fluxo de potência é resolvido com a carga fixa.

---

## Modelo de ruído de medição

Segue D'Antona et al., *IEEE Trans. Instrum. Meas.*, 2026:

| Fonte | Módulo | Ângulo | Comportamento |
|---|---|---|---|
| µPMU | ±0,2 % | ±0,2 crad | aleatório, novo sorteio a cada amostra |
| TP classe 1 | ±1 % | ±1,2 crad | sistemático, fixo por canal |
| TC classe 1 | ±1 % | ±1,8 crad | sistemático, fixo por canal |

Todos os erros são uniformes. Nos experimentos do Belvedere, o nível de ruído é controlado por um fator de escala α e pelo número K de snapshots cuja média é usada. A generalização é avaliada testando os modelos com realizações dos erros de TI diferentes das usadas no treino ("TIs não vistos").

---

## Estrutura do repositório

```text
EstimacaoFeeder/
├── Dados13barras/                          # IEEE 13 barras
│   ├── resultados_completos_0.01.csv       # dataset sem ruído
│   ├── resultados_completos_com_ruido.csv  # dataset com ruído (gerado por ComRuido.ipynb)
│   └── erros_sistematicos_TI_seed1.csv     # erros sistemáticos sorteados para os TIs
├── DadosBelvedere/                         # alimentador real do Belvedere
│   ├── 0_0_09_resultados_perturbacoes_potencia.xlsx    # abas pert_0.01 a pert_0.09
│   ├── 0_1_0_19_resultados_perturbacoes_potencia.xlsx  # abas pert_0.10 a pert_0.19
│   ├── 0_2_0_29_resultados_perturbacoes_potencia.xlsx  # abas pert_0.20 a pert_0.29
│   ├── feederlib.py                # dados, ruído, modelos, estimador bayesiano e limite teórico
│   ├── Estima_Belvedere.ipynb      # experimentos E1, E2 e E3
│   ├── resultados_belvedere.pkl    # resultados salvos dos experimentos
│   └── figuras/                    # figuras em PDF geradas pelo notebook
├── ComRuido.ipynb                  # IEEE 13: adiciona o ruído de medição ao dataset
├── Estima.ipynb                    # IEEE 13: estimação com dados sem ruído
├── Estima_Ruido.ipynb              # IEEE 13: estimação com dados com ruído
└── README.md
```

A aba `pert_0` das planilhas do Belvedere não tem variação dos parâmetros e não é usada.

---

## Notebooks

**IEEE 13 barras**
- `Estima.ipynb`: estimação com os dados sem ruído.
- `ComRuido.ipynb`: aplica o modelo de ruído (µPMU + TI) e gera `resultados_completos_com_ruido.csv`. A semente `IT_SEED` define a realização dos erros dos TIs.
- `Estima_Ruido.ipynb`: compara os modelos com e sem ruído (validação cruzada, hold-out e TIs não vistos).

**Belvedere** (`DadosBelvedere/Estima_Belvedere.ipynb`)
- **E1, posição das µPMUs:** dois terminais, só o emissor e só o receptor; dados sem ruído e perturbação de 1 %.
- **E2, nível de perturbação:** de 1 % a 29 %, sem ruído.
- **E3, ruído de µPMU + TI:** α ∈ {1; 0,1; 0,01} e K ∈ {1; 10; 100}, com perturbações de 1 %, 9 % e 29 %.

Os modelos são Ridge, MLP, LightGBM e Random Forest. A referência é o estimador bayesiano baseado na equação da linha, junto com o limite teórico de MAPE correspondente. A métrica é o MAPE por parâmetro no conjunto de teste (divisão 80/20).

O notebook carrega os resultados de `resultados_belvedere.pkl`. Para refazer todos os experimentos (cerca de 20 minutos), use `RECALCULAR = True`.

---

## Principais resultados

- **Sem ruído:** um único ponto de operação só identifica seis combinações dos 12 parâmetros. As reatâncias são bem estimadas, as resistências próprias em parte e as mútuas não.
- **IEEE 13 barras:** o estimador model-free supera o estimador ótimo baseado só na equação da linha (MAPE de 0,26 % contra 0,53 %), porque aprende a resposta da corrente ao fluxo de potência da rede a jusante.
- **Posição das µPMUs:** uma µPMU só no terminal receptor tem praticamente o mesmo desempenho que duas.
- **Com ruído realista:** o que limita a estimação é a razão sinal-ruído da queda de tensão no trecho. Um modelo treinado com uma realização dos erros dos TIs aprende o viés desses TIs e erra quando é aplicado a outros transformadores.
- **Belvedere:** o trecho de 7 m tem queda de tensão de cerca de 10⁻⁴ pu e é inobservável com µPMUs e TIs reais.

---

## Execução

```bash
git clone https://github.com/FProencadeAlbuquerque/EstimacaoFeeder.git
cd EstimacaoFeeder
pip install numpy pandas scipy scikit-learn lightgbm matplotlib openpyxl jupyter
jupyter notebook
```

Os notebooks do Belvedere devem ser executados de dentro da pasta `DadosBelvedere`, porque leem as planilhas e a `feederlib.py` da própria pasta.

---

## Autores

- Felipe Proença de Albuquerque (UFMT)
- Cássio Gerez
- Camila dos Anjos Fantin (UFMT)
- Eduardo Coelho Marques da Costa (USP)
- Raoni Florentino da Silva Teixeira (UFMT)
