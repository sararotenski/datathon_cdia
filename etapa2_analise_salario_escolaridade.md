# Etapa 2 — Análise de Salários e Escolaridade

**Projeto:** Datathon 2026 — Raio-X do Mercado de Trabalho em Santa Catarina  
**Fonte de dados:** Novo CAGED — Movimentações  
**Período analisado:** Setembro de 2025 a agosto de 2026

## 1. Objetivo

Analisar o perfil das movimentações do mercado de trabalho formal da indústria de transformação de Santa Catarina, com foco na escolaridade dos trabalhadores e nos salários de admissão e desligamento.

O objetivo é identificar diferenças entre os perfis de trabalhadores admitidos e desligados, além de observar o comportamento desses indicadores nos polos industriais do estado.

## 2. Metodologia

A análise foi realizada a partir da base tratada do Novo CAGED, armazenada em formato Parquet.

Foram desenvolvidas análises sobre:

- Distribuição da escolaridade nas admissões e nos desligamentos;
- Escolaridade por polo industrial;
- Salários medianos de admissão e desligamento por polo;
- Salários medianos por grau de instrução;
- Evolução mensal dos salários medianos.

### 2.1 Classificação da escolaridade

Os graus de instrução foram agrupados para calcular os indicadores:

- **Ensino médio completo ou mais:** códigos 7, 8, 9, 10, 11 e 80.
- **Ensino superior completo e pós-graduação:** códigos 9, 10, 11 e 80.

Registros com escolaridade não identificada (código 99) ou ausente foram excluídos das análises de escolaridade.

### 2.2 Indicadores utilizados

- **Quantidade de admissões e desligamentos:** número de movimentações registradas em cada categoria.
- **Percentual por escolaridade:** participação de cada grupo de escolaridade no total de admissões ou desligamentos considerados.
- **Salário mediano:** valor central dos salários registrados em cada grupo.
- **Diferença em pontos percentuais (p.p.):** diferença entre o percentual de admitidos e desligados em determinado grupo.
- **Diferencial salarial (%):** diferença percentual entre as medianas salariais de admissão e desligamento, calculada em relação à mediana dos desligamentos.

Os salários apresentados são nominais, sem correção pela inflação.

## 3. Resultados

### 3.1 Escolaridade geral

Na indústria de transformação foram registradas:

- 418.437 admissões;
- 417.429 desligamentos.

Entre os admitidos, 63,43% possuíam ensino médio completo ou mais. Entre os desligados, esse percentual foi de 65,47%, representando uma diferença de -2,04 pontos percentuais.

Considerando apenas ensino superior completo e pós-graduação, a participação foi de 4,77% nas admissões e 5,40% nos desligamentos, uma diferença de -0,63 p.p.

Os resultados indicam maior participação relativa de trabalhadores com escolaridade mais elevada entre os desligados do que entre os admitidos.

### 3.2 Escolaridade por polo industrial

A análise por polo revelou diferenças importantes:

- **Agroindústria:** apresentou a maior diferença na participação de trabalhadores com ensino médio completo ou mais, com -6,08 p.p.
- **Eletroeletrônico:** apresentou a maior diferença na participação de trabalhadores com ensino superior completo e pós-graduação, com -2,46 p.p.
- **Metalmecânico:** apresentou 71,89% de admitidos com ensino médio completo ou mais, uma das maiores participações entre os polos.

Esses resultados demonstram que o perfil de escolaridade das movimentações varia conforme a atividade industrial.

### 3.3 Salários por polo industrial

Em todos os sete polos analisados, a mediana salarial dos admitidos foi inferior à dos desligados.

O polo Metalmecânico apresentou as maiores medianas:

- Admitidos: R$ 2.402,40.
- Desligados: R$ 2.523,15.

O polo Eletroeletrônico apresentou o maior diferencial salarial negativo, de -6,62%.

Esse resultado indica uma diferença entre as medianas dos grupos de movimentações, mas não permite afirmar que os trabalhadores desligados individualmente recebiam mais do que passaram a receber em novos empregos.

### 3.4 Salários por escolaridade

O ensino médio completo concentrou o maior volume de movimentações, com 467.399 registros.

Os diferenciais salariais foram negativos em todos os graus de instrução analisados.

Entre os resultados:

- Mestrado: -24,36%, com 357 movimentações.
- Doutorado: -20,99%, com 120 movimentações.
- Superior completo: -9,85%, com 37.076 movimentações.
- Pós-graduação completa: -9,06%, com 4.817 movimentações.
- Superior incompleto: -4,15%.
- Ensino médio completo: -3,38%.

Os maiores diferenciais aparecem em grupos com menor volume de registros, portanto devem ser interpretados com cautela.

### 3.5 Evolução salarial mensal

Entre setembro de 2025 e agosto de 2026, observou-se crescimento das medianas salariais:

- **Admissões:** de R$ 2.118,60 para R$ 2.245,00, crescimento aproximado de 5,96%.
- **Desligamentos:** de R$ 2.200,00 para R$ 2.310,00, crescimento aproximado de 5,00%.

Em quase todo o período, a mediana salarial dos desligamentos permaneceu acima da mediana das admissões.

Dezembro de 2025 apresentou uma exceção: a mediana dos desligamentos foi de R$ 2.129,35, enquanto a das admissões foi de R$ 2.156,23.

## 4. Visualizações

Foram desenvolvidos cinco gráficos para facilitar a interpretação dos resultados:

1. `01_escolaridade_geral.png` — comparação da escolaridade nas admissões e nos desligamentos.
2. `02_escolaridade_por_polo.png` — comparação dos indicadores de escolaridade entre os polos industriais.
3. `03_salario_por_polo.png` — comparação das medianas salariais por polo.
4. `04_salario_por_escolaridade.png` — diferenciais salariais por grau de instrução.
5. `05_evolucao_salarial_mensal.png` — evolução mensal das medianas salariais.

Os arquivos estão disponíveis em `data/processados/graficos_etapa2/`.

## 5. Conclusões

A análise identificou diferenças entre os perfis de escolaridade e as medianas salariais dos trabalhadores admitidos e desligados na indústria de transformação de Santa Catarina.

Os principais resultados foram:

- A participação de trabalhadores com ensino médio completo ou mais foi maior entre os desligados.
- A Agroindústria apresentou a maior diferença na participação de trabalhadores com ensino médio completo ou mais.
- O polo Eletroeletrônico apresentou o maior diferencial negativo de salário entre os polos.
- O Metalmecânico registrou as maiores medianas salariais.
- As medianas salariais de admissão e desligamento apresentaram crescimento ao longo do período analisado.

Esses indicadores contribuem para compreender características das movimentações do mercado de trabalho industrial catarinense e podem apoiar discussões sobre qualificação profissional e demandas dos diferentes polos industriais.

## 6. Limitações

É importante considerar algumas limitações na interpretação dos resultados:

- As movimentações não representam necessariamente pessoas únicas, pois um mesmo trabalhador pode aparecer em mais de um registro.
- Admissões e desligamentos representam grupos distintos de movimentações. Portanto, a comparação entre medianas não representa a evolução salarial individual dos trabalhadores.
- Os salários são valores nominais e não foram corrigidos pela inflação.
- Grupos com poucas movimentações podem apresentar medianas menos representativas.
- As análises de escolaridade excluem registros com informação ausente ou não identificada.
- Os totais podem variar entre indicadores devido aos diferentes critérios de filtragem e à disponibilidade das informações necessárias para cada análise.

Assim, os resultados devem ser interpretados como indicadores descritivos das movimentações registradas no Novo CAGED, sem estabelecer relações de causalidade.