# Metodologia de Classificação de CBOs com Inteligência Artificial

## 1. Objetivo

Agrupar as ocupações da Classificação Brasileira de Ocupações (CBO 2002) em 20 macrofamílias, permitindo analisar o mercado de trabalho industrial de Santa Catarina de forma agregada.

## 2. Base de dados

Foram identificados 2.207 códigos CBO únicos a partir dos dados do Novo CAGED e das descrições disponíveis no dicionário da CBO.

O arquivo `cbos_unicos.csv` reúne os códigos, descrições e quantidades de movimentações.

## 3. Definição das macrofamílias

Foram estabelecidas 20 macrofamílias temáticas, contemplando atividades administrativas, industriais, comerciais, técnicas, logísticas, de serviços e demais áreas profissionais.

As categorias estão registradas no arquivo `cbo_macrofamilia.csv`.

## 4. Processo de utilização da IA

Foram desenvolvidas duas versões de prompts:

- V1: classificação com apresentação das categorias e exemplos.
- V2: classificação com definições e limites mais claros para cada macrofamília.

Os prompts foram preparados pelo script `exportar_lotes.py` e utilizados em modelos de linguagem generativa, com envio e retorno das respostas por arquivos de texto.

## 5. Avaliação dos resultados

Foi utilizada uma amostra de 100 CBOs, composta por 60 ocupações com maior número de movimentações e 40 selecionadas aleatoriamente.

As respostas foram comparadas com a classificação baseada em regras implementada em `classificar_cbo.py`.

Na avaliação da versão V2, foram obtidos:

- Concordância por quantidade de CBOs: 85%.
- Concordância ponderada pelas movimentações: 97,5%.
- Divergências identificadas: 15.

O script `importar_respostas.py` realiza a comparação e gera os arquivos `comparacao.csv` e `divergencias.csv`.

## 6. Consolidação da classificação

A classificação final dos 2.207 códigos foi gerada por meio de regras hierárquicas e exceções específicas, considerando as análises realizadas durante os testes com IA.

A IA foi utilizada como apoio à avaliação e ao aprimoramento da metodologia. Portanto, não se afirma que todos os 2.207 códigos tenham sido classificados individualmente por IA.

## 7. Limitações

- A avaliação da IA foi realizada sobre uma amostra de 100 CBOs, não sobre a totalidade dos códigos.
- Algumas ocupações podem apresentar características compatíveis com mais de uma macrofamília.
- As divergências exigem análise técnica, pois a classificação depende da atividade efetivamente exercida.
- A concordância observada na amostra não representa garantia de precisão para todos os códigos.

## 8. Reprodutibilidade

Os scripts e registros utilizados estão organizados no repositório:

- `extrair_cbos.py`
- `exportar_lotes.py`
- `importar_respostas.py`
- `classificar_cbo.py`
- `cbos_unicos.csv`
- `cbo_macrofamilia.csv`
- `llm/`

Para executar os scripts de exportação e importação, é necessário ter as dependências instaladas e os arquivos de entrada disponíveis na raiz do projeto.
