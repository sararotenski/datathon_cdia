
"""
Etapa 2 - Análises de salário e escolaridade
Projeto: Datathon 2026 - Raio-X do Mercado de Trabalho em SC

Entrada:
    data/processados/caged_mov_tratado.parquet

Saídas:
    data/processados/analises_etapa2/
        salario_por_polo.csv
        salario_por_escolaridade.csv
        salario_escolaridade_por_polo.csv
        escolaridade_por_polo.csv
        escolaridade_geral.csv
        evolucao_salarial_mensal.csv
"""

from pathlib import Path
import sys

import polars as pl
import ingestao as ing


# ============================================================
# 1. CONFIGURAÇÕES
# ============================================================

ARQUIVO_ENTRADA = (
    ing.DIR_PROCESSADOS / "caged_mov_tratado.parquet"
)

PASTA_SAIDA = (
    ing.DIR_PROCESSADOS / "analises_etapa2"
)

MIN_MOVIMENTACOES = 30

# Mesmo agrupamento de polos utilizado em src/escopo.py
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

GRAUS_SUPERIOR = [9, 10, 11, 80]
GRAUS_MEDIO_OU_MAIS = [7, 8, 9, 10, 11, 80]


# ============================================================
# 2. CARREGAMENTO E PREPARAÇÃO
# ============================================================

def carregar_base():

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO_ENTRADA}\n"
            "Execute primeiro: python src/pipeline.py"
        )

    df = pl.read_parquet(ARQUIVO_ENTRADA)

    colunas_obrigatorias = [
        "competencia_mov",
        "movimento",
        "saldo_movimentacao",
        "salario",
        "grau_instrucao",
        "secao",
        "subclasse",
        "flag_salario_atipico",
        "flag_fora_janela",
    ]

    faltantes = [
        c for c in colunas_obrigatorias
        if c not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Colunas ausentes na base: {faltantes}"
        )

    # Mesmo período utilizado na validação do escopo.
    df = df.filter(
        ~pl.col("flag_fora_janela")
    )

    # Recorte principal: indústria de transformação.
    df = df.filter(
        pl.col("secao") == "C"
    )

    # Identificação da divisão CNAE pelos dois primeiros dígitos.
    df = df.with_columns(
        pl.col("subclasse")
        .str.slice(0, 2)
        .alias("divisao_cnae")
    )

    # Associação das divisões aos polos industriais.
    mapa_polos = {
        divisao: polo
        for polo, divisoes in POLOS_INDUSTRIAIS.items()
        for divisao in divisoes
    }

    df = df.with_columns(
        pl.col("divisao_cnae")
        .replace_strict(
            mapa_polos,
            default="Sem polo"
        )
        .alias("polo")
    )

    # Mantém apenas os polos definidos no escopo.
    df = df.filter(
        pl.col("polo") != "Sem polo"
    )

    return df


# ============================================================
# 3. FUNÇÃO PARA ANÁLISE SALARIAL
# ============================================================

def analisar_salarios(df, agrupadores):

    # A exclusão de salários atípicos é aplicada
    # somente às análises de remuneração.
    base = df.filter(
        (~pl.col("flag_salario_atipico"))
        & pl.col("salario").is_not_null()
        & (pl.col("salario") > 0)
    )

    resultado = (
        base.group_by(agrupadores)
        .agg(
            pl.len().alias("total_movimentacoes"),

            (pl.col("movimento") == "admissao")
            .sum()
            .alias("n_admissoes"),

            (pl.col("movimento") == "desligamento")
            .sum()
            .alias("n_desligamentos"),

            pl.col("salario")
            .filter(pl.col("movimento") == "admissao")
            .median()
            .round(2)
            .alias("mediana_admitidos"),

            pl.col("salario")
            .filter(pl.col("movimento") == "desligamento")
            .median()
            .round(2)
            .alias("mediana_desligados"),
        )

        # Evita comparar grupos com amostras pequenas.
        .filter(
            (pl.col("n_admissoes") >= MIN_MOVIMENTACOES)
            & (pl.col("n_desligamentos") >= MIN_MOVIMENTACOES)
        )

        .with_columns(
            (
                (
                    pl.col("mediana_admitidos")
                    - pl.col("mediana_desligados")
                )
                / pl.col("mediana_desligados")
                * 100
            )
            .round(2)
            .alias("diferencial_salarial_pct")
        )
    )

    return resultado.sort(
        "diferencial_salarial_pct"
    )


# ============================================================
# 4. FUNÇÃO PARA ANÁLISE DE ESCOLARIDADE
# ============================================================

def analisar_escolaridade(df, agrupadores):

    # Escolaridade é analisada independentemente
    # da validade salarial.
    # Registros sem escolaridade identificada são excluídos.
    base = df.filter(
        pl.col("grau_instrucao").is_not_null()
        & (pl.col("grau_instrucao") != 99)
    )

    resultado = (
        base.group_by(agrupadores)
        .agg(
            (pl.col("movimento") == "admissao")
            .sum()
            .alias("n_admissoes"),

            (pl.col("movimento") == "desligamento")
            .sum()
            .alias("n_desligamentos"),

            (
                (
                    pl.col("grau_instrucao")
                    .is_in(GRAUS_MEDIO_OU_MAIS)
                    
                )
                .filter(pl.col("movimento") == "admissao")
                .mean() * 100
            )
            .round(2)
            .alias("pct_medio_ou_mais_admitidos"),

            (
                (
                    pl.col("grau_instrucao")
                    .is_in(GRAUS_MEDIO_OU_MAIS)
                )
                .filter(pl.col("movimento") == "desligamento")
                .mean() * 100
            )
            .round(2)
            .alias("pct_medio_ou_mais_desligados"),

            (
                pl.col("grau_instrucao")
                .is_in(GRAUS_SUPERIOR)
                .filter(pl.col("movimento") == "admissao")
                .mean() * 100
            )
            .round(2)
            .alias("pct_superior_admitidos"),

            (
                pl.col("grau_instrucao")
                .is_in(GRAUS_SUPERIOR)
                .filter(pl.col("movimento") == "desligamento")
                .mean() * 100
            )
            .round(2)
            .alias("pct_superior_desligados"),
        )

        .filter(
            (pl.col("n_admissoes") >= MIN_MOVIMENTACOES)
            & (pl.col("n_desligamentos") >= MIN_MOVIMENTACOES)
        )

        .with_columns(
            (
                pl.col("pct_medio_ou_mais_admitidos")
                - pl.col("pct_medio_ou_mais_desligados")
            )
            .round(2)
            .alias("diferenca_medio_ou_mais_pp"),

            (
                pl.col("pct_superior_admitidos")
                - pl.col("pct_superior_desligados")
            )
            .round(2)
            .alias("diferenca_superior_pp"),
        )
    )

    return resultado


# ============================================================
# 5. EVOLUÇÃO SALARIAL MENSAL
# ============================================================

def analisar_evolucao_salarial(df):

    base = df.filter(
        (~pl.col("flag_salario_atipico"))
        & pl.col("salario").is_not_null()
        & (pl.col("salario") > 0)
    )

    resultado = (
        base.group_by(
            ["competencia_mov", "movimento"]
        )
        .agg(
            pl.len().alias("quantidade"),
            pl.col("salario")
            .median()
            .round(2)
            .alias("salario_mediano"),
        )
        .filter(
            pl.col("quantidade") >= MIN_MOVIMENTACOES
        )
        .sort(
            ["competencia_mov", "movimento"]
        )
    )

    return resultado


# ============================================================
# 6. EXECUÇÃO E EXPORTAÇÃO
# ============================================================

def main():

    print("\nIniciando Etapa 2: salário e escolaridade...\n")

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    df = carregar_base()

    print(f"Movimentações na indústria C: {df.height:,}")

    # Análise salarial por polo.
    salario_polo = analisar_salarios(
        df,
        ["polo"]
    )

    salario_polo.write_csv(
        PASTA_SAIDA / "salario_por_polo.csv"
    )
    # Base com escolaridade identificada.
    df_escolaridade = df.filter(
       pl.col("grau_instrucao").is_not_null()
       & (pl.col("grau_instrucao") != 99)
    )

    # Análise salarial por código de escolaridade.
    salario_escolaridade = analisar_salarios(
        df_escolaridade,
        ["grau_instrucao"]
    )

    salario_escolaridade.write_csv(
        PASTA_SAIDA / "salario_por_escolaridade.csv"
    )

    # Análise salarial por polo e escolaridade.
    salario_cruzado = analisar_salarios(
        df_escolaridade,
        ["polo", "grau_instrucao"]
    )

    salario_cruzado.write_csv(
        PASTA_SAIDA / "salario_escolaridade_por_polo.csv"
    )

    # Escolaridade por polo.
    escolaridade_polo = analisar_escolaridade(
        df,
        ["polo"]
    )

    escolaridade_polo.write_csv(
        PASTA_SAIDA / "escolaridade_por_polo.csv"
    )

    # Escolaridade geral da indústria de transformação.
    base_geral = df.with_columns(
        pl.lit("Indústria de transformação").alias("recorte")
    )
 
    escolaridade_geral = analisar_escolaridade(
        base_geral,
        ["recorte"]
    )

    escolaridade_geral.write_csv(
        PASTA_SAIDA / "escolaridade_geral.csv"
    )

    # Evolução salarial mensal.
    evolucao = analisar_evolucao_salarial(df)

    evolucao.write_csv(
        PASTA_SAIDA / "evolucao_salarial_mensal.csv"
    )

    print("\nArquivos gerados com sucesso:")

    for arquivo in sorted(PASTA_SAIDA.glob("*.csv")):
        print(f" - {arquivo.name}")

    print(f"\nResultados salvos em: {PASTA_SAIDA}")

    print("\nEtapa 2 concluída!")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"\nERRO: {erro}", file=sys.stderr)
        sys.exit(1)