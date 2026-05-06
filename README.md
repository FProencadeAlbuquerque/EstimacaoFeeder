# Formulação Matemática

## Potência Complexa

A potência complexa em cada barra é definida como:

$$
S = P + jQ
$$

onde:

- $P$ é a potência ativa;
- $Q$ é a potência reativa.

A relação entre tensão e corrente é dada por:

$$
S = VI^{*}
$$

onde:

- $V$ é a tensão complexa;
- $I^{*}$ é o conjugado da corrente.

---

## Modelo de Linha

O modelo do feeder pode ser representado por uma impedância série:

$$
Z = R + jX
$$

onde:

- $R$ é a resistência da linha;
- $X$ é a reatância da linha.

A corrente elétrica é calculada por:

$$
I = \frac{S^{*}}{V^{*}}
$$

A queda de tensão ao longo do feeder é dada por:

$$
\Delta V = ZI
$$

resultando em:

$$
V_2 = V_1 - ZI
$$

---

## Problema de Estimação

O problema consiste em encontrar os parâmetros $\theta$ que minimizam o erro entre os valores medidos e os valores estimados.

O vetor de parâmetros pode ser representado por:

$$
\theta = [R, X]^T
$$

A função objetivo utilizada é baseada no erro quadrático:

$$
J(\theta)
=
\sum_{k=1}^{N}
\left(
z_k^{med}
-
z_k^{calc}(\theta)
\right)^2
$$

onde:

- $z_k^{med}$ representa as medições;
- $z_k^{calc}$ representa os valores calculados pelo modelo.

---

## Erro Percentual

O erro relativo percentual é calculado por:

$$
\mathrm{Erro}(\%)
=
\frac{
|x_{real} - x_{est}|
}{
|x_{real}|
}
\times 100
$$