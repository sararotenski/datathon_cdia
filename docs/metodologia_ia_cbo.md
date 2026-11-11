# Metodologia de Classificação de CBOs com Inteligência Artificial

## 1. Objetivo

Neste trabalho, desenvolvemos um processo para agrupar as ocupações da Classificação Brasileira de Ocupações (CBO 2002) em 20 macrofamílias. O objetivo foi organizar as diferentes ocupações em grupos mais amplos, facilitando a análise do mercado de trabalho de Santa Catarina e permitindo identificar características e tendências relacionadas aos setores profissionais.

## 2. Base de dados

A partir dos dados do Novo CAGED, identificamos 2.207 códigos CBO únicos, considerando as ocupações presentes na base de movimentações.

Também utilizamos o dicionário da CBO para relacionar os códigos às respectivas descrições. O resultado dessa etapa está organizado no arquivo `cbos_unicos.csv`, que reúne os códigos, as descrições das ocupações e suas quantidades de movimentações.

## 3. Definição das macrofamílias

Para organizar as ocupações, definimos 20 macrofamílias temáticas, considerando as características das atividades profissionais e os setores aos quais elas estão relacionadas.

A divisão contempla áreas como administração, comércio, saúde, educação, construção civil, indústria, logística, tecnologia e serviços.

As categorias foram organizadas no arquivo `cbo_macrofamilia.csv`, que contém a classificação atribuída a cada código CBO.

## 4. Utilização da Inteligência Artificial

Utilizamos modelos de linguagem generativa como apoio ao processo de classificação, principalmente para avaliar se as macrofamílias estavam bem definidas e se as regras utilizadas produziam resultados coerentes.

Para isso, desenvolvemos duas versões de prompts:

- **V1:** apresentava as macrofamílias disponíveis, algumas regras de classificação e exemplos de resposta.
- **V2:** além das regras e exemplos, incluía definições para cada macrofamília, deixando mais claro quais tipos de ocupação deveriam pertencer a cada grupo.

Os prompts foram desenvolvidos no script `exportar_lotes.py`, que organiza as ocupações em lotes de texto. Como o processo foi realizado manualmente, copiamos os lotes para os modelos de IA e salvamos as respostas recebidas em arquivos `.txt`.

Dessa forma, conseguimos testar diferentes instruções e comparar os resultados sem depender de uma integração automática por API.

## 5. Avaliação dos resultados

Para avaliar o comportamento dos prompts, utilizamos uma amostra de 100 CBOs, composta por:

- 60 ocupações com maior número de movimentações;
- 40 ocupações selecionadas aleatoriamente, utilizando uma semente fixa para manter a reprodutibilidade da seleção.

Após receber as respostas dos modelos, comparamos as classificações com aquelas produzidas pelo script `classificar_cbo.py`.

Na versão V2, os resultados foram:

- **Concordância por quantidade de CBOs:** 85%;
- **Concordância ponderada pelas movimentações:** 97,5%;
- **Divergências identificadas:** 15.

A concordância ponderada considera o volume de movimentações de cada ocupação. Por isso, ocupações com maior participação na base possuem maior peso no cálculo.

Desenvolvemos o script `importar_respostas.py` para organizar as respostas, comparar as classificações e gerar os arquivos `comparacao.csv` e `divergencias.csv`.

As divergências foram utilizadas como ponto de partida para revisar casos específicos e avaliar possíveis ajustes nas regras de classificação.

## 6. Consolidação da classificação

Após os testes com os modelos de linguagem, analisamos as divergências encontradas e revisamos as classificações que precisavam de ajustes.

Com base nessa análise, incluímos exceções específicas no script `classificar_cbo.py`, complementando as regras hierárquicas utilizadas para classificar as ocupações.

A classificação final dos 2.207 códigos foi gerada por esse script, combinando regras baseadas nos códigos CBO e exceções definidas durante a revisão.

É importante destacar que utilizamos a IA como ferramenta de apoio à avaliação e ao aprimoramento da metodologia. A classificação final não foi feita individualmente por IA para todos os 2.207 códigos.

## 7. Limitações

Durante o desenvolvimento, identificamos alguns pontos que precisam ser considerados na interpretação dos resultados:

- A avaliação dos modelos de IA foi realizada sobre uma amostra de 100 CBOs, e não sobre a totalidade das ocupações.
- Algumas ocupações apresentam características que podem se encaixar em mais de uma macrofamília, exigindo análise do contexto e da atividade exercida.
- As divergências entre a classificação por regras e as respostas da IA não representam necessariamente erros de um dos métodos. Elas indicam situações que precisam de avaliação.
- Os índices de concordância obtidos na amostra não garantem o mesmo nível de concordância para todos os códigos CBO.

Por isso, os resultados devem ser interpretados considerando os critérios adotados e as decisões realizadas durante a classificação.

## 8. Organização e reprodutibilidade

Organizamos os scripts, as bases utilizadas e os registros dos testes no repositório do projeto, permitindo consultar as etapas realizadas e reproduzir parte do processo.

Os principais arquivos são:

- `extrair_cbos.py`: extrai e organiza os códigos CBO presentes nos dados.
- `exportar_lotes.py`: prepara os lotes de ocupações e os prompts utilizados nos testes com IA.
- `importar_respostas.py`: importa as respostas dos modelos e compara as classificações.
- `classificar_cbo.py`: aplica as regras e exceções utilizadas na classificação final.
- `cbos_unicos.csv`: reúne os códigos CBO, suas descrições e quantidades de movimentações.
- `cbo_macrofamilia.csv`: apresenta a classificação final das ocupações.
- `llm/`: armazena os prompts, as respostas e os resultados das comparações das versões V1 e V2.

Para executar o processo de extração, também são necessários os arquivos de origem dentro da pasta `dados/`, incluindo o arquivo de movimentações do Novo CAGED e o dicionário da CBO. Esses arquivos de origem não estão incluídos nesta parte do repositório.

Os scripts de exportação, importação e classificação utilizam os arquivos CSV organizados na raiz do projeto como entrada.
