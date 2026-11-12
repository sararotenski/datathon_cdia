# Validação do escopo da pergunta de negócio

> **Pergunta central:** "Quais regiões e setores industriais de Santa Catarina estão enfrentando apagão de mão de obra ou expansão acelerada, e como os indicadores de renda e escolaridade explicam esses gargalos?"

Base: `caged_mov_tratado.parquet`, competências 09/2025 a 08/2026 (3.391.288 movimentações; 6.128 declarações atrasadas de meses anteriores ficam de fora). Números gerados por `src/escopo.py` (detalhe em `data/processados/escopo_etapa1.json`).

## Resumo

| Parte da pergunta | A base sustenta? | Observação |
|---|---|---|
| Setores industriais | Sim | Seção C = 24,6% das movimentações; todas as divisões mapeiam para os polos do guia |
| Regiões | **Não, sem dado externo** | Só há código de município; nenhum dos arquivos traz micro/mesorregião |
| Expansão acelerada | Sim | Saldo + população 2026 permitem "saldo por 10 mil habitantes" |
| Apagão de mão de obra | **Só por proxy** | O CAGED não tem vagas abertas nem estoque de empregos |
| Renda | Sim | Salário com 0,17% de valores atípicos na indústria |
| Escolaridade | Sim | Nenhum registro "não identificado" na indústria |
| Agrupar mais de 200 CBOs por IA | Sim | 203 CBOs cobrem 90% das movimentações da indústria |

## 1. Setores industriais

| Recorte | Movimentações | % da base | Saldo 12 meses |
|---|---:|---:|---:|
| C – Indústria de transformação | 835.866 | 24,6% | +1.008 |
| B a F – Indústria ampla (CNI: extrativa, transformação, eletricidade/gás, água/resíduos, construção) | 1.139.633 | 33,6% | +2.645 |

Todos os polos citados no guia (seção 2.1) estão na seção C. Agrupando as divisões CNAE (2 primeiros dígitos da subclasse):

| Polo (divisões CNAE) | Movimentações | Saldo | % deslig. a pedido |
|---|---:|---:|---:|
| Agroindústria (10–12) | 184.962 | +4.542 | 55,6% |
| Metalmecânico (24, 25, 28–30, 33) | 178.307 | +3.459 | 45,6% |
| Eletroeletrônico (26–27) | 42.338 | +1.646 | 50,1% |
| Química, plástico, minerais não metálicos (19–23) | 115.430 | −236 | 48,5% |
| Outras (18, 32) | 19.339 | −297 | 48,2% |
| Madeira, papel e móveis (16, 17, 31) | 100.312 | −2.190 | 52,3% |
| Têxtil, vestuário e couro (13–15) | 195.178 | −5.916 | 52,4% |

O saldo da indústria de transformação no estado é quase nulo (+1.008 sobre 418 mil admissões). A história está na diferença entre polos e regiões: agro e metalmecânico crescem, têxtil e madeira encolhem.

**Decisão pendente:** usar só a seção C (alinhada aos polos do guia) ou B a F (inclui construção, que tem 272 mil movimentações e mudaria bastante os resultados).

## 2. Regiões

Os dados têm só `municipio_codigo`. O guia pede "microrregiões" (seção 2.3) e cita regiões como Vale do Itajaí, Norte, Oeste e Grande Florianópolis (seção 2.1), que correspondem às mesorregiões do IBGE.

A API de localidades do IBGE (`servicodados.ibge.gov.br/api/v1/localidades/estados/42/municipios`) devolve, para cada município, microrregião, mesorregião, região imediata e região intermediária, com o código IBGE de 7 dígitos (mesma chave já tratada).

**Decisão pendente:** incorporar essa tabela (dado externo, precisa ser citado no pitch) e escolher o nível: mesorregião (6 regiões, bate com o vocabulário do guia) ou microrregião (20 regiões, mais detalhe).

## 3. Expansão acelerada

Sustentada: saldo por município/setor e `populacao_estimada_2026` (sem nulos) permitem a métrica "saldo por 10 mil habitantes" pedida no guia.

Cuidado com a sazonalidade: dezembro/2025 teve saldo de −48.616, e jan–mar/2026 somaram +59.534. Comparar meses isolados distorce; usar o acumulado de 12 meses ou comparar o mesmo mês.

## 4. Apagão de mão de obra

O guia define apagão como alta demanda com escassez de profissionais qualificados ou forte rotatividade. O CAGED registra só fluxos (admissões e desligamentos). Faltam:

- **vagas abertas/não preenchidas**: não dá para medir escassez diretamente;
- **estoque de empregos**: não dá para calcular a taxa de rotatividade oficial (que divide pelo estoque).

Proxies possíveis com a base:

| Proxy | O que indica | Valor na seção C |
|---|---|---:|
| % de desligamentos a pedido (tipo 40) | Trabalhador sai por conta própria: mercado aquecido, disputa por mão de obra | 50,9% (base toda: 47,1%) |
| Giro = (admissões + desligamentos) ÷ \|saldo\| | Muito movimento para pouco crescimento: reposição constante | calcular por célula |
| Salário de admissão ÷ salário de desligamento | Abaixo de 1: empresa repõe pagando menos (pode afastar candidatos) | 0,97 (mediana) |
| Escolaridade de admitidos x desligados | Repõe com perfil menos qualificado | 63,4% x 65,5% com médio completo ou mais |

Se o estoque for necessário, a fonte seria a RAIS ou o estoque publicado pelo MTE (dado externo).

**Decisão pendente:** quais proxies compõem o indicador de apagão. Esta é uma premissa a declarar no pitch.

## 5. Renda e escolaridade

Sustentadas, com boa qualidade na seção C: 0,17% de salários fora da faixa 0,3–150 salários mínimos e nenhum grau de instrução "não identificado".

Primeiro sinal, só na seção C e no agregado: admitidos ganham menos (mediana R$ 2.175,80 contra R$ 2.250,00 dos desligados) e têm escolaridade um pouco menor. Isso conversa com a pergunta do guia sobre compressão salarial, mas precisa ser testado por polo, região e CBO.

Use `salario` (mensal) nas análises. `valor_salario_fixo` pode estar por hora ou dia.

## 6. Granularidade

Cruzando município × divisão da seção C, há 3.105 combinações. Muitas são pequenas:

| Mínimo de movimentações na célula | Células | % das movimentações cobertas |
|---:|---:|---:|
| 30 | 1.631 | 98,3% |
| 100 | 1.020 | 94,2% |
| 500 | 363 | 76,0% |

Recomendação: exigir pelo menos 30 movimentações por célula para calcular médias e percentuais, e preferir região × polo no painel principal.

## 7. CBOs para o agrupamento por IA

A seção C tem 1.467 CBOs distintos (482 famílias de 4 dígitos). Os 203 mais frequentes cobrem 90% das movimentações, o que bate com o "mais de 200 CBOs" do guia. Sugestão: mandar à IA esses 203 e agrupar o resto pela família de 4 dígitos.

## Limites a declarar no pitch

1. Exclusões (EXC) não aplicadas: premissa de que a base "_Limpo" já vem sem elas.
2. Apagão medido por proxies, sem dados de vagas nem de estoque.
3. Empresas de trabalho temporário (subclasse 7820500, 97.517 movimentações) ficam na seção N, mesmo quando o trabalhador atua na indústria.
4. Regiões dependem de tabela externa do IBGE.
5. Microdados sem identificador: não dá para seguir a trajetória de uma pessoa (quem saiu foi para onde).

```
### Matriz de Especificação dos KPIs do Projeto

| Indicador (KPI) | Fórmula Matemática | Fonte &amp; Campos | Recorte / Filtro | Categoria no Dashboard (Sarah) |
| :--- | :--- | :--- | :--- | :--- |
| **Saldo Líquido de Vagas** | `SUM(saldomovimentação)` | CAGED: `saldomovimentação` | SC (`uf=42`), Indústria (`C, F, B`) | Visão Geral Executiva |
| **Saldo por 10k Hab.** | `(Saldo / População) * 10.000` | CAGED + IBGE (`População estimada`) | Por Município / Microrregião | Mapa de Expansão e Apagão |
| **Taxa de Turnover (%)** | `(Desligamentos / (Admissões + Desligamentos)) * 100` | CAGED: `saldomovimentação`, `tipomovimentação` | Por Setor CNAE e Município | Diagnóstico de Estabilidade |
| **Diferencial Salarial (%)** | `((Salário_Adm - Salário_Dem) / Salário_Dem) * 100` | CAGED: `salário`, `saldomovimentação` | Por Grau de Instrução e CBO | Painel Socioeconômico |