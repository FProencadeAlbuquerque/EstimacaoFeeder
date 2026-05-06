# EstimacaoFeeder

Projeto voltado à estimação de parâmetros elétricos de um feeder utilizando medições elétricas, fluxo de potência e técnicas de otimização e regressão.

---

# Objetivo

O objetivo principal deste projeto é estimar parâmetros elétricos equivalentes de um sistema de distribuição a partir de medições de tensão, corrente e potência.

A metodologia considera:

- Modelagem elétrica do feeder;
- Fluxo de potência;
- Estimação iterativa de parâmetros;
- Avaliação do erro entre valores medidos e calculados;
- Comparação entre parâmetros reais e estimados.

---

# Descrição do Problema

O sistema elétrico é representado por um modelo equivalente contendo parâmetros como resistência e reatância das linhas do feeder.

A partir das medições elétricas disponíveis, o algoritmo realiza:

- Cálculo das grandezas elétricas;
- Estimação dos parâmetros do sistema;
- Minimização do erro entre medições e valores calculados;
- Avaliação da precisão da estimação.

O projeto utiliza conceitos de:

- Potência complexa;
- Impedância elétrica;
- Fluxo de potência;
- Estimação paramétrica;
- Otimização numérica.

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

- Python
- NumPy
- Pandas
- SciPy
- Matplotlib
- Jupyter Notebook

---

# Execução

## Clone o repositório

```bash
git clone https://github.com/FProencadeAlbuquerque/EstimacaoFeeder.git
```

## Acesse a pasta do projeto

```bash
cd EstimacaoFeeder
```

## Execute o notebook

```bash
jupyter notebook
```

ou execute diretamente o script Python:

```bash
python Estima.py
```

---

# Resultados

O projeto fornece:

- Parâmetros estimados do feeder;
- Erros percentuais;
- Comparação entre valores reais e estimados;
- Arquivos CSV contendo os resultados completos;
- Avaliação do desempenho da metodologia de estimação.

---

# Aplicações

A metodologia pode ser aplicada em:

- Sistemas de distribuição;
- Smart grids;
- Identificação de parâmetros elétricos;
- Estimação de estados;
- Modelagem de feeders reais;
- Estudos de operação e planejamento de sistemas elétricos.

---

# Autores

- Felipe Proença
- Cássio Gerez
- Camila Fantin