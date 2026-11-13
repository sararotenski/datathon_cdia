
"""
Etapa 3 - Análise setorial do mercado de trabalho
Projeto: Datathon 2026 - Raio-X do Mercado de Trabalho em SC

Período: setembro/2025 a agosto/2026

Entradas:
    data/processados/caged_mov_tratado.parquet

Saídas:
    data/processados/analises_etapa3/indicadores_etapa3.csv
    data/processados/graficos_etapa3/
        01_ranking_divisoes.png
        02_saldo_por_polo.png
        03_evolucao_mensal.png
    etapa3_analise_setorial.md
"""

from pathlib import Path

import polars as pl
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

ARQUIVO_ENTRADA = (
    BASE_DIR / "data" / "processados" / "caged_mov_tratado.parquet"
)

PASTA_ANALISES = (
    BASE_DIR / "data" / "processados" / "analises_etapa3"
)

PASTA_GRAFICOS = (
    BASE_DIR / "data" / "processados" / "graficos_etapa3"
)

ARQUIVO_CSV = PASTA_ANALISES / "indicadores_etapa3.csv"
ARQUIVO_MD = BASE_DIR / "etapa3_analise_setorial.md"

INICIO = 202509
FIM = 202608

# Classificação já utilizada na Etapa 2.
POLOS_INDUSTRIAIS = {
    "Agroindústria": ["10", "11", "12"],
    "Têxtil, vestuário e couro": ["13", "14", "15"],
    "Metalmecânico": ["24", "25", "28", "29", "30", "33"],
    "Eletroeletrônico": ["26", "27"],
    "Madeira, papel e móveis": ["16", "17", "31"],
    "Química, plástico e minerais não metálicos": [
        "19", "20", "21", "22", "23"
    ],
    "Outras": ["18", "32"],
}

POLO_POR_DIVISAO = {
    divisao: polo
    for polo, divisoes in POLOS_INDUSTRIAIS.items()
    for divisao in divisoes
}


# ============================================================
# 2. FUNÇÕES AUXILIARES
# ============================================================

def agregar(df: pl.DataFrame, coluna: str, tipo: str) -> pl.DataFrame:
    """Calcula admissões, desligamentos e saldo por categoria."""

    resultado = (
        df.group_by(coluna)
        .agg([
            (pl.col("saldo_movimentacao") > 0)
            .sum()
            .alias("admissoes"),

            (pl.col("saldo_movimentacao") < 0)
            .sum()
            .alias("desligamentos"),

            pl.col("saldo_movimentacao")
            .sum()
            .alias("saldo"),
        ])
        .rename({coluna: "categoria"})
        .with_columns([
            pl.lit(tipo).alias("tipo_analise"),
            pl.lit(None, dtype=pl.String).alias("competencia"),
        ])
        .select([
            "tipo_analise",
            "categoria",
            "competencia",
            "admissoes",
            "desligamentos",
            "saldo",
        ])
        .sort("saldo", descending=True)
    )

    return resultado


def salvar_grafico(caminho: Path):
    plt.tight_layout()
    plt.savefig(caminho, dpi=300, bbox_inches="tight")
    plt.close()



# ============================================================
# 3. PREPARAÇÃO DA BASE
# ============================================================

def main():

    PASTA_ANALISES.mkdir(parents=True, exist_ok=True)
    PASTA_GRAFICOS.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("ETAPA 3 - ANÁLISE SETORIAL")
    print("=" * 65)

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO_ENTRADA}"
        )

    print("\n1. Carregando base tratada...")

    df = pl.read_parquet(
        ARQUIVO_ENTRADA,
        columns=[
            "competencia_mov",
            "secao",
            "subclasse",
            "saldo_movimentacao",
        ],
    )

    # Recorte explícito dos 12 meses da análise.
    df = (
        df.filter(
            pl.col("competencia_mov").is_between(INICIO, FIM)
        )
        .with_columns(
            pl.col("subclasse")
            .str.slice(0, 2)
            .alias("divisao_cnae")
        )
    )

    if df.is_empty():
        raise ValueError("Não existem registros no período selecionado.")

    print(f"Movimentações no período: {df.height:,}".replace(",", "."))


    # ========================================================
    # 4. RANKING POR DIVISÃO CNAE
    # ========================================================

    print("\n2. Calculando saldo por divisão CNAE...")

    base_divisoes = df.filter(
        pl.col("divisao_cnae").is_not_null()
    )

    ranking_divisoes = agregar(
        base_divisoes,
        "divisao_cnae",
        "divisao_cnae",
    )

    # Rótulos identificam os códigos, sem inventar descrições.
    ranking_divisoes = ranking_divisoes.with_columns(
        pl.concat_str(
            [pl.lit("Divisão "), pl.col("categoria")]
        ).alias("categoria")
    )


    # ========================================================
    # 5. RANKING DOS POLOS INDUSTRIAIS
    # ========================================================

    print("\n3. Calculando saldo por polo industrial...")

    base_polos = (
        df.filter(pl.col("secao") == "C")
        .with_columns(
            pl.col("divisao_cnae")
            .replace_strict(
                POLO_POR_DIVISAO,
                default="Sem polo",
            )
            .alias("polo")
        )
        .filter(pl.col("polo") != "Sem polo")
    )

    ranking_polos = agregar(
        base_polos,
        "polo",
        "polo_industrial",
    )


    # ========================================================
    # 6. EVOLUÇÃO MENSAL
    # ========================================================

    print("\n4. Calculando evolução mensal...")

    mensal_total = (
        df.group_by("competencia_mov")
        .agg([
            (pl.col("saldo_movimentacao") > 0)
            .sum()
            .alias("admissoes"),

            (pl.col("saldo_movimentacao") < 0)
            .sum()
            .alias("desligamentos"),

            pl.col("saldo_movimentacao")
            .sum()
            .alias("saldo"),
        ])
        .with_columns([
            pl.lit("Total da base").alias("categoria"),
            pl.lit("evolucao_mensal").alias("tipo_analise"),
            pl.col("competencia_mov")
            .cast(pl.String)
            .alias("competencia"),
        ])
        .drop("competencia_mov")
    )

    mensal_industria = (
        df.filter(pl.col("secao") == "C")
        .group_by("competencia_mov")
        .agg([
            (pl.col("saldo_movimentacao") > 0)
            .sum()
            .alias("admissoes"),

            (pl.col("saldo_movimentacao") < 0)
            .sum()
            .alias("desligamentos"),

            pl.col("saldo_movimentacao")
            .sum()
            .alias("saldo"),
        ])
        .with_columns([
            pl.lit("Indústria de transformação").alias("categoria"),
            pl.lit("evolucao_mensal").alias("tipo_analise"),
            pl.col("competencia_mov")
            .cast(pl.String)
            .alias("competencia"),
        ])
        .drop("competencia_mov")
    )

    mensal = pl.concat(
        [mensal_total, mensal_industria]
    ).select([
        "tipo_analise",
        "categoria",
        "competencia",
        "admissoes",
        "desligamentos",
        "saldo",
    ])


    # ========================================================
    # 7. CONSOLIDAÇÃO DO CSV
    # ========================================================

    print("\n5. Consolidando indicadores...")

    indicadores = pl.concat([
        ranking_divisoes,
        ranking_polos,
        mensal,
    ])

    indicadores.write_csv(ARQUIVO_CSV)

    print(f"CSV salvo: {ARQUIVO_CSV}")


    
    # ========================================================
    # 8. GRÁFICO - DIVISÕES CNAE
    # ========================================================

    print("\n6. Gerando gráficos...")

    dados_divisoes = (
        ranking_divisoes
        .sort("saldo")
        .to_pandas()
    )

    positivos = dados_divisoes[
        dados_divisoes["saldo"] > 0
    ].tail(10)

    negativos = dados_divisoes[
        dados_divisoes["saldo"] < 0
    ].head(10)

    grafico_divisoes = pd.concat([
        negativos,
        positivos,
    ]).drop_duplicates(subset=["categoria"])

    # Nomes das atividades econômicas conforme a CNAE.
    nomes_divisoes = {
        "81": "Serviços para edifícios e atividades paisagísticas",
        "10": "Fabricação de produtos alimentícios",
        "73": "Publicidade e pesquisa de mercado",
        "86": "Atividades de atenção à saúde humana",
        "82": "Serviços de escritório e apoio administrativo",
        "46": "Comércio por atacado",
        "78": "Seleção, agenciamento e locação de mão de obra",
        "52": "Armazenamento e atividades auxiliares dos transportes",
        "49": "Transporte terrestre",
        "47": "Comércio varejista",
        "42": "Obras de infraestrutura",
        "25": "Fabricação de produtos de metal",
        "26": "Fabricação de equipamentos eletrônicos e ópticos",
        "84": "Administração pública",
        "15": "Preparação de couros e fabricação de calçados",
        "13": "Fabricação de produtos têxteis",
        "23": "Fabricação de produtos de minerais não metálicos",
        "31": "Fabricação de móveis",
        "16": "Fabricação de produtos de madeira",
        "14": "Confecção de artigos do vestuário e acessórios",
    }

    codigos = grafico_divisoes["categoria"].str.replace(
        "Divisão ", "", regex=False
    )

    grafico_divisoes["nome_atividade"] = codigos.map(
        nomes_divisoes
    ).fillna(grafico_divisoes["categoria"])

    plt.figure(figsize=(14, 9))

    barras = plt.barh(
        grafico_divisoes["nome_atividade"],
        grafico_divisoes["saldo"],
    )

    plt.axvline(0, linewidth=0.8)

    limite = grafico_divisoes["saldo"].abs().max() * 1.15
    plt.xlim(-limite, limite)

    for barra in barras:
        valor = barra.get_width()
        deslocamento = limite * 0.015

        plt.text(
            valor + deslocamento if valor >= 0 else valor - deslocamento,
            barra.get_y() + barra.get_height() / 2,
            f"{valor:+,.0f}".replace(",", "."),
            va="center",
            ha="left" if valor >= 0 else "right",
        )

    plt.title(
        "10 divisões CNAE com maiores ganhos e maiores perdas"
    )
    plt.xlabel("Saldo de movimentações")
    plt.ylabel("Atividade econômica")
    salvar_grafico(
        PASTA_GRAFICOS / "01_ranking_divisoes.png"
    )

    
    # ========================================================
    # 9. GRÁFICO - POLOS INDUSTRIAIS
    # ========================================================

    dados_polos = ranking_polos.to_pandas().sort_values("saldo")

    plt.figure(figsize=(13, 7))

    barras = plt.barh(
        dados_polos["categoria"],
        dados_polos["saldo"],
    )

    plt.axvline(0, linewidth=0.8)

    limite = dados_polos["saldo"].abs().max() * 1.15
    plt.xlim(-limite, limite)

    for barra in barras:
        valor = barra.get_width()
        deslocamento = limite * 0.015

        plt.text(
            valor + deslocamento if valor >= 0 else valor - deslocamento,
            barra.get_y() + barra.get_height() / 2,
            f"{valor:+,.0f}".replace(",", "."),
            va="center",
            ha="left" if valor >= 0 else "right",
        )

    plt.title(
        "Saldo de movimentações por polo da indústria de transformação"
    )
    plt.xlabel("Saldo de movimentações")
    plt.ylabel("Polo industrial")

    salvar_grafico(
        PASTA_GRAFICOS / "02_saldo_por_polo.png"
    )


    
    # ========================================================
    # 10. GRÁFICO - EVOLUÇÃO MENSAL
    # ========================================================

    dados_mensais = mensal.to_pandas()

    dados_mensais["competencia"] = pd.to_datetime(
        dados_mensais["competencia"],
        format="%Y%m",
    )

    plt.figure(figsize=(12, 6))

    for categoria, grupo in dados_mensais.groupby("categoria"):
        grupo = grupo.sort_values("competencia")

        plt.plot(
            grupo["competencia"],
            grupo["saldo"],
            marker="o",
            label=categoria,
        )

    plt.axhline(0, linewidth=0.8)

    plt.title("Evolução mensal do saldo de movimentações")
    plt.xlabel("Competência")
    plt.ylabel("Saldo de movimentações")
    plt.legend()
    plt.xticks(rotation=45)

    salvar_grafico(
        PASTA_GRAFICOS / "03_evolucao_mensal.png"
    )


        # ========================================================
    # 11. DOCUMENTAÇÃO AUTOMÁTICA
    # ========================================================

    print("\n7. Gerando documentação...")

    total_admissoes = int(
        (df["saldo_movimentacao"] > 0).sum()
    )
    total_desligamentos = int(
        (df["saldo_movimentacao"] < 0).sum()
    )
    saldo_geral = int(df["saldo_movimentacao"].sum())

    melhor_divisao = (
        dados_divisoes.sort_values("saldo", ascending=False)
        .iloc[0]
    )
    pior_divisao = (
        dados_divisoes.sort_values("saldo")
        .iloc[0]
    )

    melhor_polo = (
        dados_polos.sort_values("saldo", ascending=False)
        .iloc[0]
    )
    pior_polo = (
        dados_polos.sort_values("saldo")
        .iloc[0]
    )

    texto = f"""# Etapa 3 — Análise setorial do mercado de trabalho

## Objetivo

Identificar divisões de atividade econômica e polos industriais
com expansão ou retração líquida de empregos formais em Santa Catarina.

## Período analisado

Setembro de 2025 a agosto de 2026.

## Indicadores gerais

- Admissões: {total_admissoes:,}
- Desligamentos: {total_desligamentos:,}
- Saldo líquido: {saldo_geral:+,}

## Divisões CNAE

- Maior saldo positivo: {melhor_divisao['categoria']}
  ({int(melhor_divisao['saldo']):+,})
- Menor saldo: {pior_divisao['categoria']}
  ({int(pior_divisao['saldo']):+,})

## Polos industriais

- Maior saldo positivo: {melhor_polo['categoria']}
  ({int(melhor_polo['saldo']):+,})
- Menor saldo: {pior_polo['categoria']}
  ({int(pior_polo['saldo']):+,})

## Metodologia

A análise utiliza a base tratada do CAGED MOV.

O saldo é calculado pela soma da variável `saldo_movimentacao`,
que representa +1 para admissões e -1 para desligamentos.

As divisões CNAE são identificadas pelos dois primeiros dígitos
do código de subclasse.

A análise dos polos considera a seção C da CNAE
(indústria de transformação) e reutiliza a classificação
de polos definida na Etapa 2.

## Limitações

Os resultados representam movimentações de vínculos formais,
não pessoas únicas nem vagas abertas.

Saldo positivo indica mais admissões do que desligamentos
no período; saldo negativo indica o contrário.

A análise não permite, isoladamente, estabelecer relações
de causalidade.

## Arquivos gerados

- `indicadores_etapa3.csv`
- `01_ranking_divisoes.png`
- `02_saldo_por_polo.png`
- `03_evolucao_mensal.png`
"""

    texto = texto.replace(",", ".")

    ARQUIVO_MD.write_text(texto, encoding="utf-8")

    print(f"Documentação salva: {ARQUIVO_MD}")

    print("\n" + "=" * 65)
    print("ETAPA 3 CONCLUÍDA")
    print("=" * 65)
    print(f"Indicadores: {ARQUIVO_CSV}")
    print(f"Gráficos: {PASTA_GRAFICOS}")
    print(f"Documentação: {ARQUIVO_MD}")


if __name__ == "__main__":
    main()


