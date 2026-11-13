# Validação do escopo da pergunta de negócio

> **Pergunta central:** "Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?"

**Base utilizada:** `caged_mov_tratado.parquet`, considerando as competências de 09/2025 a 08/2026, com 3.391.288 movimentações. As 6.128 declarações atrasadas, referentes a meses anteriores, foram desconsideradas.

Os números apresentados foram gerados pelo script `src/escopo.py`. Os detalhes podem ser consultados em `data/processados/escopo_etapa1.json`.

## Resumo

| Parte da pergunta | Os dados permitem responder? | Observação |
|---|---|---|
| Setores industriais | Sim | A seção C representa 24,6% das movimentações, e suas divisões podem ser agrupadas conforme os polos definidos no guia. |
| Regiões | Não, sem dados externos | A base possui apenas o código do município. Nenhum dos arquivos utilizados contém a divisão por micro ou mesorregião. |
| Expansão acelerada | Sim | O saldo de movimentações e a população estimada para 2026 permitem calcular o saldo por 10 mil habitantes. |
| Apagão de mão de obra | Parcialmente, por meio de indicadores indiretos | O CAGED não apresenta informações sobre vagas abertas ou estoque de empregos. |
| Renda | Sim | Os salários apresentam boa qualidade na seção C, com 0,17% de valores atípicos. |
| Escolaridade | Sim | Não encontramos registros com grau de instrução "não identificado" na indústria. |
| Agrupamento de CBOs por IA | Sim | Os 203 CBOs mais frequentes representam 90% das movimentações da indústria. |

## 1. Setores industriais

Identificamos que a base permite analisar os setores industriais por meio da Classificação Nacional de Atividades Econômicas (CNAE).

| Recorte | Movimentações | % da base | Saldo 12 meses |
|---|---:|---:|---:|
| C – Indústria de transformação | 835.866 | 24,6% | +1.008 |
| B a F – Indústria ampla (extrativa, transformação, eletricidade e gás, água e resíduos e construção) | 1.139.633 | 33,6% | +2.645 |

Verificamos que todos os polos industriais citados no guia (seção 2.1) estão contemplados na seção C. Para analisar esses polos, agrupamos as divisões CNAE, considerando os dois primeiros dígitos dos códigos das subclasses.

| Polo (divisões CNAE) | Movimentações | Saldo | % deslig. a pedido |
|---|---:|---:|---:|
| Agroindústria (10–12) | 184.962 | +4.542 | 55,6% |
| Metalmecânico (24, 25, 28–30, 33) | 178.307 | +3.459 | 45,6% |
| Eletroeletrônico (26–27) | 42.338 | +1.646 | 50,1% |
| Química, plástico, minerais não metálicos (19–23) | 115.430 | −236 | 48,5% |
| Outras (18, 32) | 19.339 | −297 | 48,2% |
| Madeira, papel e móveis (16, 17, 31) | 100.312 | −2.190 | 52,3% |
| Têxtil, vestuário e couro (13–15) | 195.178 | −5.916 | 52,4% |

Os resultados mostram comportamentos diferentes entre os polos industriais. Agroindústria e metalmecânico apresentam saldos positivos, enquanto têxtil e madeira apresentam saldos negativos.

No agregado estadual, o saldo da indústria de transformação é próximo de zero (+1.008), considerando aproximadamente 418 mil admissões. Portanto, entendemos que é importante analisar as diferenças entre os polos, em vez de considerar apenas o resultado geral da indústria.

**Decisão pendente:** precisamos definir se utilizaremos apenas a seção C, que está alinhada aos polos apresentados no guia, ou o agrupamento de B a F, que também inclui a construção civil, responsável por 272 mil movimentações e capaz de alterar os resultados.

## 2. Regiões

Identificamos que os dados disponíveis possuem apenas o campo `municipio_codigo`, sem informações sobre a divisão regional dos municípios.

O guia solicita uma análise por microrregiões (seção 2.3) e também cita regiões como Vale do Itajaí, Norte, Oeste e Grande Florianópolis (seção 2.1).

Para complementar essa informação, podemos utilizar a API de localidades do IBGE:

`servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios`

A API disponibiliza informações sobre microrregiões, mesorregiões, regiões imediatas e regiões intermediárias de cada município, utilizando o código IBGE de sete dígitos, que corresponde à chave já tratada na nossa base.

**Decisão pendente:** precisamos definir qual divisão regional será utilizada. Consideramos duas possibilidades:

- **Mesorregiões:** seis regiões, permitindo uma análise mais ampla e uma divisão compatível com a regionalização mencionada no guia.
- **Microrregiões:** vinte regiões, possibilitando uma análise mais detalhada.

Caso utilizemos essa informação, devemos identificar e citar o IBGE como fonte complementar no pitch.

## 3. Expansão acelerada

Verificamos que os dados permitem analisar a expansão dos setores e municípios por meio do saldo de admissões e desligamentos.

Além disso, a presença do campo `populacao_estimada_2026`, sem valores nulos, permite calcular o saldo por 10 mil habitantes, facilitando a comparação entre municípios de diferentes tamanhos populacionais.

Também identificamos a necessidade de considerar a sazonalidade nas análises. Em dezembro de 2025, por exemplo, o saldo foi de −48.616 movimentações, enquanto janeiro a março de 2026 somaram +59.534.

Por isso, recomendamos utilizar o acumulado dos 12 meses ou comparar os mesmos meses entre períodos diferentes, evitando conclusões baseadas em variações isoladas.

## 4. Apagão de mão de obra

O guia define o apagão de mão de obra como uma situação de alta demanda, acompanhada de escassez de profissionais qualificados ou forte rotatividade.

Ao analisar as informações disponíveis, identificamos uma limitação importante: o CAGED registra os fluxos de admissões e desligamentos, mas não permite medir diretamente a quantidade de vagas abertas ou o estoque total de empregos.

Com isso, não conseguimos identificar diretamente a escassez de profissionais nem calcular a taxa oficial de rotatividade, que depende do estoque de trabalhadores.

Como alternativa, podemos utilizar indicadores indiretos para investigar possíveis sinais de gargalos no mercado de trabalho:

| Indicador | O que podemos observar | Valor na seção C |
|---|---|---:|
| % de desligamentos a pedido (tipo 40) | Pode indicar maior movimentação voluntária dos trabalhadores e possíveis disputas por profissionais. | 50,9% (base toda: 47,1%) |
| Giro = (admissões + desligamentos) ÷ valor absoluto do saldo | Ajuda a identificar situações com muitas movimentações e pouco crescimento líquido do emprego. | Calcular por célula |
| Salário de admissão ÷ salário de desligamento | Permite comparar os salários de entrada e saída dos trabalhadores. | 0,97 (mediana) |
| Escolaridade de admitidos x desligados | Permite observar diferenças no nível de escolaridade entre os trabalhadores admitidos e desligados. | 63,4% x 65,5% com médio completo ou mais |

É importante considerar que esses indicadores funcionam como aproximações e não comprovam, isoladamente, a existência de um apagão de mão de obra.

Também precisamos ter cuidado com o indicador de giro, pois, quando o saldo se aproxima de zero, o resultado pode ficar muito elevado. Por isso, recomendamos analisá-lo junto com o volume de movimentações e outros indicadores.

Caso seja necessário utilizar informações sobre o estoque de empregos, podemos recorrer à RAIS ou aos dados de estoque publicados pelo Ministério do Trabalho e Emprego, identificando essas fontes como complementares.

**Decisão pendente:** precisamos definir quais indicadores serão utilizados na composição do indicador de apagão de mão de obra. Essa escolha deverá ser explicada no pitch, deixando claras as premissas adotadas pela equipe.

## 5. Renda e escolaridade

Identificamos que as informações de renda e escolaridade apresentam boa qualidade na seção C.

Na análise dos salários, encontramos apenas 0,17% de valores fora da faixa de 0,3 a 150 salários mínimos. Também não encontramos registros com grau de instrução "não identificado" na indústria.

Uma primeira observação, considerando o agregado da seção C, é que os trabalhadores admitidos apresentam salário mediano menor do que os desligados: R$ 2.175,80 contra R$ 2.250,00.

Também observamos uma diferença na escolaridade: 63,4% dos admitidos possuem ensino médio completo ou superior, enquanto entre os desligados esse percentual é de 65,5%.

Esses resultados podem indicar diferenças no perfil dos trabalhadores e nas condições de remuneração, mas ainda precisamos aprofundar a análise por polo industrial, região e CBO para identificar possíveis relações com os gargalos do mercado de trabalho.

Para as análises, recomendamos utilizar o campo `salario`, que representa o salário mensal. O campo `valor_salario_fixo` pode estar relacionado a valores por hora ou por dia, dependendo do registro.

## 6. Granularidade

Ao cruzarmos município e divisão da seção C, encontramos 3.105 combinações. No entanto, percebemos que algumas possuem poucas movimentações, o que pode comprometer a análise de médias e percentuais.

| Mínimo de movimentações na célula | Células | % das movimentações cobertas |
|---:|---:|---:|
| 30 | 1.631 | 98,3% |
| 100 | 1.020 | 94,2% |
| 500 | 363 | 76,0% |

Com base nesses resultados, recomendamos utilizar pelo menos 30 movimentações por célula para calcular médias e percentuais.

Para o painel principal, consideramos mais adequado trabalhar com o cruzamento entre região e polo industrial, pois essa divisão permite visualizar os resultados de forma mais clara, sem perder uma parcela significativa das movimentações.

## 7. CBOs para o agrupamento por IA

Na seção C, identificamos 1.467 CBOs distintos, distribuídos em 482 famílias de quatro dígitos.

Verificamos que os 203 CBOs mais frequentes representam 90% das movimentações da indústria, o que atende à proposta do guia de trabalhar com mais de 200 ocupações.

Como estratégia, recomendamos utilizar esses 203 códigos no processo de agrupamento com IA. Para as demais ocupações, podemos avaliar a possibilidade de utilizar o agrupamento pela família de quatro dígitos, considerando que códigos pertencentes à mesma família podem apresentar atividades diferentes.

Essa abordagem permite concentrar a análise de IA nas ocupações com maior participação nas movimentações, mantendo uma estratégia de classificação para os códigos restantes.
