# Etapa 3 — Análise setorial do mercado de trabalho

## Objetivo

Identificar divisões de atividade econômica e polos industriais
com expansão ou retração líquida de empregos formais em Santa Catarina.

## Período analisado

Setembro de 2025 a agosto de 2026.

## Indicadores gerais

- Admissões: 1.716.341
- Desligamentos: 1.674.947
- Saldo líquido: +41.394

## Divisões CNAE

- Maior saldo positivo: Divisão 81
  (+4.864)
- Menor saldo: Divisão 14
  (-4.571)

## Polos industriais

- Maior saldo positivo: Agroindústria
  (+4.542)
- Menor saldo: Têxtil. vestuário e couro
  (-5.916)

## Metodologia

A análise utiliza a base tratada do CAGED MOV.

O saldo é calculado pela soma da variável `saldo_movimentacao`.
que representa +1 para admissões e -1 para desligamentos.

As divisões CNAE são identificadas pelos dois primeiros dígitos
do código de subclasse.

A análise dos polos considera a seção C da CNAE
(indústria de transformação) e reutiliza a classificação
de polos definida na Etapa 2.

## Limitações

Os resultados representam movimentações de vínculos formais.
não pessoas únicas nem vagas abertas.

Saldo positivo indica mais admissões do que desligamentos
no período; saldo negativo indica o contrário.

A análise não permite. isoladamente. estabelecer relações
de causalidade.

## Arquivos gerados

- `indicadores_etapa3.csv`
- `01_ranking_divisoes.png`
- `02_saldo_por_polo.png`
- `03_evolucao_mensal.png`
