# EstimacaoFeeder

Projeto voltado à estimação de parâmetros elétricos de um feeder utilizando medições elétricas, fluxo de potência e técnicas de otimização/regressão.

---

# Objetivo

O objetivo principal deste projeto é estimar parâmetros elétricos equivalentes de um sistema de distribuição a partir de medições de tensão, corrente e potência.

A metodologia considera:

* Modelo elétrico do feeder;
* Fluxo de potência;
* Estimação iterativa dos parâmetros;
* Avaliação do erro entre valores medidos e calculados.

---

# Formulação Matemática

## Potência Complexa

A potência complexa em cada barra é definida como:

[
S = P + jQ
]

onde:

* (P) é a potência ativa;
* (Q) é a potência reativa.

A relação entre tensão e corrente é dada por:

[
S = VI^*
]

onde:

* (V) é a tensão complexa;
* (I^*) é o conjugado da corrente.

---

## Modelo de Linha

O modelo do feeder pode ser representado por uma impedância série:

[
Z = R + jX
]

onde:

* (R) é a resistência da linha;
* (X) é a reatância da linha.

A corrente elétrica é calculada por:

[
I = \frac{S^*}{V^*}
]

A queda de tensão ao longo do feeder é dada por:

[
\Delta V = ZI
]

resultando em:

[
V_2 = V_1 - ZI
]

---

## Problema de Estimação

O problema consiste em encontrar os parâmetros (\theta) que minimizam o erro entre os valores medidos e os valores estimados.

O vetor de parâmetros pode ser representado por:

[
\theta = [R, X]^T
]

A função objetivo utilizada é baseada no erro quadrático:

[
J(\theta) = \sum_{k=1}^{N} ||z_k^{med} - z_k^{calc}(\theta)||^2
]

onde:

* (z_k^{med}) representa as medições;
* (z_k^{calc}) representa os valores calculados pelo modelo.

---

## Erro Percentual

O erro relativo percentual é calculado por:

[
Erro(%) = \frac{|x_{real} - x_{est}|}{|x_{real}|} \times 100
]

---

# Estrutura do Projeto

```text
EstimacaoFeeder/
│
├── Estima.ipynb
├── Estima.py
├── resultados_completos_0.01.csv
├── README.md
```

---

# Tecnologias Utilizadas

* Python
* NumPy
* Pandas
* SciPy
* Matplotlib
* Jupyter Notebook

---

# Execução

## Clone o repositório

```bash
git clone https://github.com/FProencadeAlbuquerque/EstimacaoFeeder.git
```

## Acesse a pasta

```bash
cd EstimacaoFeeder
```

## Execute o notebook

```bash
jupyter notebook
```

ou execute o script:

```bash
python Estima.py
```

---

# Resultados

O projeto fornece:

* Parâmetros estimados do feeder;
* Erros percentuais;
* Comparação entre valores reais e estimados;
* Arquivos CSV contendo os resultados completos.

---

# Aplicações

A metodologia pode ser aplicada em:

* Sistemas de distribuição;
* Smart grids;
* Identificação de parâmetros;
* Estimação de estados;
* Modelagem de feeders reais.

---

# Autor

Felipe Proença
