Planejamento das Análises de Salário e Escolaridade

## 1. Objetivo

Planejar as análises de renda e escolaridade dos trabalhadores da indústria catarinense, comparando admitidos e desligados para identificar possíveis diferenças de remuneração, qualificação profissional e dificuldades de retenção de mão de obra.

As análises deverão responder aos questionamentos apresentados no Guia do Participante sobre o perfil dos profissionais contratados, a compressão salarial e a adequação da qualificação às necessidades da indústria.

## 2. Base de dados e variáveis

Será utilizada a base tratada do Novo CAGED, considerando as competências de setembro de 2025 a agosto de 2026.

Variáveis necessárias:

| Variável | Utilização |
|---|---|
| `salario` | Análise da remuneração mensal |
| `grau_instrucao` | Identificação da escolaridade |
| `saldo_movimentacao` | Separação de admissões e desligamentos |
| `secao` | Identificação do setor industrial |
| `subclasse` | Identificação da atividade econômica |
| `municipio_codigo` | Comparação territorial |
| `cbo2002_ocupacao` | Identificação das ocupações |
| `competencia_mov` | Evolução temporal |

## 3. Planejamento das análises salariais

### 3.1 Comparação salarial entre admitidos e desligados

Calcular a mediana salarial dos trabalhadores admitidos e desligados.

Fórmula:

Diferencial salarial (%) = [(Mediana dos admitidos − Mediana dos desligados) / Mediana dos desligados] × 100.

Objetivo: identificar se os novos trabalhadores estão sendo contratados com remunerações inferiores ou superiores às dos profissionais desligados.

### 3.2 Comparação salarial entre polos industriais

Agrupar as atividades econômicas nos polos industriais definidos pelo projeto:

- Agroindústria;
- Têxtil, vestuário e couro;
- Metalmecânico;
- Eletroeletrônico;
- Madeira, papel e móveis;
- Química, plástico e minerais não metálicos;
- Outras atividades industriais.

Calcular as medianas salariais de admitidos e desligados para cada polo.

Objetivo: identificar quais setores apresentam maiores diferenças de remuneração.

### 3.3 Comparação salarial por escolaridade

Agrupar os trabalhadores conforme o grau de instrução e calcular as medianas salariais de admitidos e desligados em cada nível.

Objetivo: verificar se existe relação entre formação educacional e remuneração, identificando possíveis situações de desvalorização salarial de profissionais qualificados.

## 4. Planejamento das análises de escolaridade

### 4.1 Comparação da escolaridade entre admitidos e desligados

Calcular:

- Percentual de trabalhadores com ensino médio completo ou superior.
- Percentual de trabalhadores com ensino superior ou pós-graduação.

Comparar os resultados entre admitidos e desligados.

Objetivo: identificar possíveis mudanças no perfil educacional dos trabalhadores contratados.

### 4.2 Escolaridade por polo industrial

Realizar a mesma comparação de escolaridade separadamente para cada polo industrial.

Objetivo: identificar quais setores estão contratando trabalhadores com diferentes níveis de formação em relação aos profissionais desligados.

### 4.3 Relação entre salário e escolaridade

Cruzar os níveis de escolaridade com as medianas salariais, separando admitidos e desligados.

Objetivo: verificar se as remunerações acompanham os níveis de qualificação profissional e identificar possíveis diferenças entre os polos industriais.

## 5. Critérios metodológicos

1. Utilizar a indústria de transformação (seção C) como recorte principal, conforme a proposta de escopo do grupo.
2. Utilizar a coluna `salario`, sem misturá-la com `valor_salario_fixo`.
3. Excluir salários classificados como atípicos por meio da flag `flag_salario_atipico`.
4. Considerar o período de setembro de 2025 a agosto de 2026.
5. Separar admissões e desligamentos pela variável `saldo_movimentacao`.
6. Utilizar a mediana como medida principal de remuneração.
7. Exigir pelo menos 30 movimentações por agrupamento.
8. Comparar os resultados por polo industrial, região, escolaridade e ocupação, respeitando a disponibilidade dos dados.

## 6. Visualizações planejadas

| Visualização | Informação apresentada |
|---|---|
| Gráfico de barras | Comparação salarial entre admitidos e desligados |
| Barras agrupadas | Escolaridade dos admitidos e desligados |
| Gráfico de dispersão | Relação entre salário e escolaridade |
| Gráfico de linhas | Evolução salarial por competência |

As visualizações serão desenvolvidas para apoiar a construção do dashboard analítico do projeto.

## 7. Resultados preliminares disponíveis

Na validação inicial da indústria de transformação, foram identificados os seguintes valores:

| Indicador | Admitidos | Desligados |
|---|---:|---:|
| Salário mediano | R$ 2.175,80 | R$ 2.250,00 |
| Ensino médio completo ou superior | 63,4% | 65,5% |
| Ensino superior ou pós-graduação | 4,8% | 5,4% |

Os resultados preliminares indicam salários medianos inferiores entre os admitidos e uma participação ligeiramente menor de trabalhadores com maior escolaridade.

Esses resultados deverão ser aprofundados por polo industrial, região e ocupação antes de qualquer conclusão definitiva.

## 8. Resultado esperado

Ao concluir as análises, espera-se identificar:

- Diferenças salariais entre admitidos e desligados.
- Setores que apresentam possíveis problemas de atratividade financeira.
- Níveis de escolaridade predominantes na indústria.
- Diferenças de qualificação entre trabalhadores contratados e desligados.
- Relações entre remuneração, escolaridade e possíveis gargalos de mão de obra.

**Responsável:** Maria — Indicadores e Análises.

**Documento de referência:** Guia do Participante — Datathon 2026.
