Definição dos Indicadores do Projeto (KPIs)

## 1. Objetivo

Definir os indicadores-chave de desempenho (KPIs) que serão utilizados para analisar o mercado de trabalho industrial de Santa Catarina, identificando regiões e setores com expansão acelerada, possíveis dificuldades de retenção e possíveis gargalos de qualificação profissional.

Os indicadores também deverão permitir relacionar renda e escolaridade às movimentações de emprego, conforme a pergunta central do projeto:

"Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?"

## 2. Indicadores definidos

### KPI 1 — Saldo Líquido de Vagas

**Objetivo:** identificar os setores e municípios que estão criando ou perdendo postos de trabalho.

**Fórmula:**

Saldo líquido = Total de admissões − Total de desligamentos

Na base do Novo CAGED, será utilizada a soma da variável `saldomovimentação`.

**Campos utilizados:**
- `saldomovimentação`
- `competênciamov`
- `município`
- `seção`
- `subclasse`

**Interpretação:**
- Saldo positivo: mais admissões do que desligamentos.
- Saldo negativo: mais desligamentos do que admissões.
- Saldo próximo de zero: equilíbrio entre admissões e desligamentos.

**Aplicação:** identificar os setores e regiões com maior expansão ou retração do emprego industrial.

### KPI 2 — Saldo de Vagas por 10 Mil Habitantes

**Objetivo:** comparar a expansão do mercado de trabalho entre municípios de diferentes tamanhos populacionais.

**Fórmula:**

Saldo por 10 mil habitantes = (Saldo líquido de vagas / População estimada) × 10.000

**Campos utilizados:**
- `saldomovimentação`
- `município`
- População estimada de 2026 (base do IBGE).

**Interpretação:**
- Resultado positivo: expansão proporcional do emprego.
- Resultado negativo: retração proporcional do emprego.
- Resultado próximo de zero: pouca variação proporcional.

**Aplicação:** identificar municípios com expansão acelerada ou retração, permitindo comparações territoriais mais justas.

### KPI 3 — Percentual de Desligamentos a Pedido

**Objetivo:** investigar possíveis dificuldades de retenção de trabalhadores nos setores industriais.

**Fórmula:**

Percentual de desligamentos a pedido = (Quantidade de desligamentos a pedido / Total de desligamentos) × 100

Será identificado o desligamento a pedido por meio do código de movimentação 40, conforme a classificação utilizada no tratamento da base.

**Campos utilizados:**
- `tipomovimentação`
- `saldomovimentação`
- `seção`
- `subclasse`
- `município`
- `competênciamov`

**Interpretação:**
- Percentual elevado: maior participação de saídas voluntárias.
- Percentual reduzido: menor participação desse tipo de desligamento.

**Aplicação:** identificar setores e regiões nos quais pode existir maior dificuldade de retenção de profissionais.

Esse indicador será utilizado como uma evidência de possível pressão sobre a mão de obra, não como comprovação isolada de apagão.

### KPI 4 — Diferencial Salarial entre Admitidos e Desligados

**Objetivo:** verificar se os salários oferecidos aos novos trabalhadores acompanham os valores recebidos pelos profissionais desligados.

**Fórmula:**

Diferencial salarial (%) = [(Mediana salarial dos admitidos − Mediana salarial dos desligados) / Mediana salarial dos desligados] × 100

Será utilizada a mediana da coluna `salário`, que representa o salário mensal.

**Campos utilizados:**
- `salário`
- `saldomovimentação`
- `graudeinstrução`
- `subclasse`
- `cbo2002ocupação`
- `município`

**Interpretação:**
- Resultado positivo: salário mediano dos admitidos superior ao dos desligados.
- Resultado negativo: salário mediano dos admitidos inferior ao dos desligados.
- Resultado próximo de zero: valores salariais semelhantes.

**Aplicação:** investigar a atratividade salarial das oportunidades de emprego e identificar possíveis diferenças entre setores, regiões e níveis de escolaridade.

### KPI 5 — Perfil de Escolaridade dos Trabalhadores

**Objetivo:** identificar o nível de formação dos trabalhadores admitidos e desligados, verificando possíveis diferenças de qualificação profissional.

Serão utilizados dois indicadores complementares:

**A) Percentual de trabalhadores com ensino médio completo ou superior**

Fórmula:

(Quantidade de trabalhadores com ensino médio completo ou superior / Total de trabalhadores) × 100

**B) Percentual de trabalhadores com ensino superior**

Fórmula:

(Quantidade de trabalhadores com ensino superior / Total de trabalhadores) × 100

**Campos utilizados:**
- `graudeinstrução`
- `saldomovimentação`
- `subclasse`
- `cbo2002ocupação`
- `município`

Os códigos de escolaridade serão agrupados conforme o dicionário da base do Novo CAGED.

**Interpretação:**
- Maior percentual de escolaridade: maior participação de trabalhadores com formação naquele nível.
- Diferenças entre admitidos e desligados: possíveis mudanças no perfil de qualificação da mão de obra.

**Aplicação:** relacionar escolaridade, salários e movimentações de emprego para identificar possíveis dificuldades de reposição de profissionais qualificados.

## 3. Indicadores complementares

Além dos cinco KPIs principais, poderão ser utilizados indicadores auxiliares:

| Indicador | Fórmula | Finalidade |
|---|---|---|
| Participação das admissões | Admissões / Total de movimentações × 100 | Avaliar a participação das contratações |
| Participação dos desligamentos | Desligamentos / Total de movimentações × 100 | Avaliar a participação das saídas |
| Giro de movimentações | (Admissões + Desligamentos) / Valor absoluto do saldo | Identificar movimentação elevada em relação ao crescimento líquido |

O indicador de giro deverá ser interpretado com cautela, pois pode apresentar valores muito elevados quando o saldo estiver próximo de zero.

## 4. Dimensões de análise

Os indicadores serão analisados considerando as seguintes dimensões:

| Dimensão | Variáveis |
|---|---|
| Territorial | Município e região |
| Setorial | Seção, divisão e subclasse CNAE |
| Temporal | Competência de movimentação |
| Salarial | Salário mensal |
| Educacional | Grau de instrução |
| Ocupacional | CBO |
| Movimentação | Admissões e desligamentos |

Para as análises territoriais, será utilizada a integração com a base de localidades do IBGE, permitindo associar os municípios às respectivas regiões.

A escolha entre microrregiões e mesorregiões deverá ser validada pela equipe, considerando a correspondência com as regiões apresentadas no Guia do Participante.

## 5. Critérios metodológicos

Para garantir a consistência dos resultados, serão adotados os seguintes critérios:

1. Utilizar os registros tratados do arquivo `Novo_Caged_MOV_Limpo.csv`.
2. Utilizar a coluna `salário` nas análises de remuneração.
3. Separar admissões e desligamentos por meio da variável `saldomovimentação`.
4. Comparar os indicadores por município, região e setor industrial.
5. Utilizar a população estimada de 2026 para calcular o saldo por 10 mil habitantes.
6. Priorizar agrupamentos com pelo menos 30 movimentações para o cálculo de médias e percentuais.
7. Utilizar a mediana nas comparações salariais.
8. Considerar o período efetivamente disponível e validado na base integrada.

**Recorte setorial proposto:** utilizar a seção C (Indústria de Transformação) como análise principal, por sua correspondência com os polos industriais apresentados no guia. A inclusão das seções B a F deverá ser validada pela equipe antes da consolidação dos resultados.

## 6. Identificação de possíveis gargalos de mão de obra

O apagão de mão de obra será investigado por meio da combinação dos indicadores definidos.

Serão observados principalmente:

- Expansão das admissões e saldo positivo de vagas.
- Participação elevada de desligamentos a pedido.
- Salários de admissão inferiores aos de desligamento.
- Diferenças de escolaridade entre admitidos e desligados.

A combinação desses fatores permitirá identificar regiões e setores com possíveis dificuldades de retenção, reposição ou qualificação profissional.

**Limitação:** o Novo CAGED registra movimentações de emprego, mas não informa diretamente o número de vagas abertas e não preenchidas nem o estoque total de trabalhadores. Portanto, os indicadores constituem evidências indiretas de pressão sobre a mão de obra e não permitem comprovar isoladamente a existência de apagão.

## 7. Aplicação no Dashboard

Os indicadores serão disponibilizados para apoiar a construção do dashboard analítico, contemplando:

| Área do dashboard | Indicadores |
|---|---|
| Visão Geral Executiva | Saldo líquido de vagas |
| Expansão Territorial | Saldo por 10 mil habitantes |
| Diagnóstico de Retenção | Percentual de desligamentos a pedido |
| Painel Socioeconômico | Diferencial salarial |
| Qualificação Profissional | Perfil de escolaridade |

Os gráficos deverão permitir comparações entre regiões, setores e períodos, facilitando a identificação dos principais gargalos do mercado de trabalho industrial catarinense.

## 8. Resultado esperado

Com a definição dos indicadores, o projeto terá uma base metodológica para:

- Identificar setores industriais em expansão ou retração.
- Comparar o desempenho do mercado de trabalho entre municípios e regiões.
- Investigar possíveis dificuldades de retenção de trabalhadores.
- Avaliar diferenças salariais entre admitidos e desligados.
- Relacionar escolaridade e qualificação às movimentações de emprego.
- Produzir evidências para recomendações estratégicas à indústria catarinense.

**Responsável pela definição:** Maria — Indicadores e Análises.

**Documento de referência:** Guia do Participante — Datathon 2026.
