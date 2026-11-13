"""Etapa 4a - Indicadores para o dashboard.

Gera ``data/processados/base_dashboard.parquet``: movimentações da indústria
(seções B a F) dentro da janela de 12 meses, com região IBGE, polo industrial e
nível de qualificação do CBO. As funções de agregação e classificação são
usadas pelo dashboard (``dashboard/app.py``) para recalcular tudo conforme os
filtros escolhidos.

Indicadores (por recorte região x setor):
    Expansão     saldo, saldo por 10 mil habitantes, saldo relativo (saldo / admissões)
    Rotatividade % dos desligamentos que foram a pedido do trabalhador (tipo 40)
    Renda        salário mediano de admissão ÷ salário mediano de desligamento
    Escolaridade p.p. de admitidos com médio completo ou mais, menos o mesmo % dos desligados

Classificação (comparada à média estadual do recorte selecionado):
    Sinais de apagão = quantos destes ocorrem:
        rotatividade  % a pedido >= referência + LIMIAR_PEDIDO_PP
        renda         razão salarial <= referência - LIMIAR_RAZAO
        qualificação  gap de escolaridade <= -LIMIAR_ESCOLARIDADE_PP
    Situação:
        Expansão com gargalo   expansão acelerada e >= 2 sinais
        Expansão acelerada     saldo relativo >= LIMIAR_EXPANSAO e saldo por 10 mil hab >= LIMIAR_POR_10MIL
        Sinal de apagão        >= 2 sinais
        Retração               saldo relativo <= -LIMIAR_EXPANSAO ou
                               saldo por 10 mil hab <= -LIMIAR_RETRACAO_10MIL
        Estável                demais casos
    Recortes com menos de MIN_MOVIMENTACOES ficam como "Volume insuficiente".

Uso: .venv/bin/python src/indicadores.py   (requer a saída de src/integracao.py)
"""

from __future__ import annotations

import json
import sys

import polars as pl

import ingestao as ing
from erros import ErroArquivo, ErroPipeline, ErroSchema, ErroValidacao, avisar

ARQ_REGIOES = ing.DIR_BRUTOS / "regioes_ibge_sc.json"   # API de localidades do IBGE
ARQ_MALHA = ing.DIR_BRUTOS / "malha_municipios_sc.geojson"  # API de malhas do IBGE
ARQ_BASE = ing.DIR_PROCESSADOS / "base_dashboard.parquet"
# Classificação dos CBOs em macrofamílias (etapa 3, docs/metodologia_ia_cbo.md).
ARQ_MACROFAMILIAS = ing.RAIZ / "cbo_macrofamilia.csv"
SEM_MACROFAMILIA = "Não classificado"

SECOES_INDUSTRIA = {
    "B": "Indústria extrativa",
    "C": "Indústria de transformação",
    "D": "Eletricidade e gás",
    "E": "Água, esgoto e resíduos",
    "F": "Construção",
}
# Polos da seção C citados no guia, por divisão CNAE (2 primeiros dígitos).
POLOS_C = {
    "Agroindústria": ["10", "11", "12"],
    "Têxtil e vestuário": ["13", "14", "15"],
    "Madeira, papel e móveis": ["16", "17", "31"],
    "Química, plásticos e minerais": ["19", "20", "21", "22", "23"],
    "Metalmecânico": ["24", "25", "28", "29", "30", "33"],
    "Eletroeletrônico": ["26", "27"],
    "Outras indústrias": ["18", "32"],
}
POLO_POR_DIVISAO = {d: p for p, divs in POLOS_C.items() for d in divs}

# Grande grupo da CBO (1º dígito). Agrupamento provisório até a etapa de IA.
GRANDE_GRUPO_CBO = {
    "0": "Forças armadas e segurança",
    "1": "Dirigentes e gerentes",
    "2": "Profissionais das ciências (engenharia, TI etc.)",
    "3": "Técnicos de nível médio",
    "4": "Administrativos",
    "5": "Serviços e comércio",
    "6": "Agropecuária",
    "7": "Produção industrial (operadores)",
    "8": "Produção industrial (processos contínuos)",
    "9": "Manutenção e reparação",
}
NIVEL_QUALIFICACAO = {
    "0": "Outros", "1": "Gestão e engenharia/técnicos", "2": "Gestão e engenharia/técnicos",
    "3": "Gestão e engenharia/técnicos", "4": "Administrativo e serviços",
    "5": "Administrativo e serviços", "6": "Operacional", "7": "Operacional",
    "8": "Operacional", "9": "Operacional",
}
NIVEIS_REGIAO = {
    "Mesorregião": "mesorregiao",
    "Microrregião": "microrregiao",
    "Região intermediária": "regiao_intermediaria",
    "Região imediata": "regiao_imediata",
    "Município": "municipio_nome",
}

TIPO_A_PEDIDO = 40
GRAU_MEDIO_COMPLETO = 7
POR_HABITANTES = 10_000
MIN_MOVIMENTACOES = 500
LIMIAR_EXPANSAO = 0.05        # saldo / admissões
LIMIAR_POR_10MIL = 3.0
# Polos grandes perdem muitas vagas com saldo relativo pequeno (ex.: têxtil no Vale).
LIMIAR_RETRACAO_10MIL = 10.0
LIMIAR_PEDIDO_PP = 3.0
LIMIAR_RAZAO = 0.02
LIMIAR_ESCOLARIDADE_PP = 3.0

ORDEM_SITUACAO = ["Expansão com gargalo", "Expansão acelerada", "Sinal de apagão",
                  "Estável", "Retração", "Volume insuficiente"]


# --------------------------------------------------------------------------- #
# Construção da base
# --------------------------------------------------------------------------- #
def carregar_regioes() -> pl.DataFrame:
    ing.checar_arquivo(ARQ_REGIOES, "Regiões IBGE (API de localidades)")
    try:
        bruto = json.loads(ARQ_REGIOES.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErroArquivo(f"'{ARQ_REGIOES.name}' não é um JSON válido. {e}") from e
    df = pl.DataFrame(bruto)
    esperadas = {"municipio-id", "mesorregiao-nome", "microrregiao-nome",
                 "regiao-intermediaria-nome", "regiao-imediata-nome"}
    if not esperadas <= set(df.columns):
        raise ErroSchema(f"'{ARQ_REGIOES.name}': faltam colunas {sorted(esperadas - set(df.columns))}")
    df = df.select(
        pl.col("municipio-id").cast(pl.String).str.slice(0, 6).alias("municipio_codigo"),
        pl.col("mesorregiao-nome").alias("mesorregiao"),
        pl.col("microrregiao-nome").alias("microrregiao"),
        pl.col("regiao-intermediaria-nome").alias("regiao_intermediaria"),
        pl.col("regiao-imediata-nome").alias("regiao_imediata"),
    )
    if df["municipio_codigo"].is_duplicated().any():
        raise ErroValidacao(f"'{ARQ_REGIOES.name}': município repetido.")
    return df


def carregar_macrofamilias() -> pl.DataFrame:
    ing.checar_arquivo(ARQ_MACROFAMILIAS, "Macrofamílias de CBO (etapa de IA)")
    try:
        m = pl.read_csv(ARQ_MACROFAMILIAS, infer_schema=False)
    except pl.exceptions.PolarsError as e:
        raise ErroArquivo(f"'{ARQ_MACROFAMILIAS.name}' ilegível. {e}") from e
    if not {"codigo", "macrofamilia"} <= set(m.columns):
        raise ErroSchema(f"'{ARQ_MACROFAMILIAS.name}' precisa das colunas 'codigo' e 'macrofamilia'.")
    m = m.select(
        pl.col("codigo").str.strip_chars().str.zfill(6).alias("cbo2002_ocupacao"),
        pl.col("macrofamilia").str.strip_chars().alias("macrofamilia_cbo"),
    )
    repetidos = m.filter(pl.col("cbo2002_ocupacao").is_duplicated())["cbo2002_ocupacao"].unique().to_list()
    if repetidos:
        raise ErroValidacao(f"'{ARQ_MACROFAMILIAS.name}': CBO repetido: {repetidos[:10]}")
    return m


def construir_base() -> pl.DataFrame:
    origem = ing.DIR_PROCESSADOS / "caged_territorial.parquet"
    if not origem.exists():
        raise ErroArquivo(f"'{origem.name}' não encontrado. Rode antes src/pipeline.py e src/integracao.py.")
    regioes = carregar_regioes()
    cols = ["competencia_mov", "municipio_codigo", "municipio_nome", "codigo_ibge", "secao",
            "subclasse", "cbo2002_ocupacao", "saldo_movimentacao", "tipo_movimentacao", "salario",
            "grau_instrucao", "sexo", "idade", "flag_salario_atipico", "flag_fora_janela"]
    df = (
        pl.scan_parquet(origem).select(cols)
        .filter(~pl.col("flag_fora_janela") & pl.col("secao").is_in(list(SECOES_INDUSTRIA)))
        .drop("flag_fora_janela")
        .collect()
    )
    divisao = pl.col("subclasse").str.slice(0, 2)
    gg = pl.col("cbo2002_ocupacao").str.slice(0, 1)
    df = df.with_columns(
        secao_nome=pl.col("secao").replace_strict(SECOES_INDUSTRIA),
        divisao=divisao,
        polo=pl.when(pl.col("secao") == "C")
        .then(divisao.replace_strict(POLO_POR_DIVISAO, default="Outras indústrias"))
        .otherwise(pl.col("secao").replace_strict(SECOES_INDUSTRIA)),
        cbo_grande_grupo=gg.replace_strict(GRANDE_GRUPO_CBO, default="Não classificado"),
        nivel_qualificacao=gg.replace_strict(NIVEL_QUALIFICACAO, default="Outros"),
        salario=pl.col("salario").cast(pl.Float32),
    ).join(regioes, on="municipio_codigo", how="left", validate="m:1") \
     .join(carregar_macrofamilias(), on="cbo2002_ocupacao", how="left", validate="m:1") \
     .with_columns(pl.col("macrofamilia_cbo").fill_null(SEM_MACROFAMILIA))

    sem_macro = df.filter(pl.col("macrofamilia_cbo") == SEM_MACROFAMILIA).height
    if sem_macro:
        avisar(f"{sem_macro:,} movimentação(ões) com CBO fora de '{ARQ_MACROFAMILIAS.name}' "
               f"(marcadas como '{SEM_MACROFAMILIA}').")

    sem_regiao = df.filter(pl.col("mesorregiao").is_null()).height
    if sem_regiao:
        raise ErroValidacao(f"{sem_regiao:,} linha(s) sem região IBGE após o join.")
    cat = ["municipio_nome", "secao", "secao_nome", "polo", "cbo_grande_grupo", "nivel_qualificacao",
           "macrofamilia_cbo",
           "mesorregiao", "microrregiao", "regiao_intermediaria", "regiao_imediata", "divisao"]
    return df.with_columns(pl.col(cat).cast(pl.Categorical))


def populacao_por_regiao() -> pl.DataFrame:
    mun = pl.read_parquet(ing.DIR_PROCESSADOS / "municipios_sc.parquet")
    return mun.select("municipio_codigo", "municipio_nome", "codigo_ibge", "populacao_estimada_2026") \
        .join(carregar_regioes(), on="municipio_codigo", how="left", validate="1:1")


# --------------------------------------------------------------------------- #
# Indicadores
# --------------------------------------------------------------------------- #
def agregar(df: pl.DataFrame, por: list[str]) -> pl.DataFrame:
    """Fluxos, renda e escolaridade por grupo. ``por`` pode ser vazio (total)."""
    adm = pl.col("saldo_movimentacao") == 1
    desl = ~adm
    sal_ok = ~pl.col("flag_salario_atipico")
    medio = pl.col("grau_instrucao") >= GRAU_MEDIO_COMPLETO
    exprs = [
        pl.len().alias("movimentacoes"),
        adm.sum().alias("admissoes"),
        desl.sum().alias("desligamentos"),
        pl.col("saldo_movimentacao").sum().alias("saldo"),
        (pl.col("tipo_movimentacao") == TIPO_A_PEDIDO).sum().alias("desl_a_pedido"),
        pl.col("salario").filter(adm & sal_ok).median().alias("salario_admissao"),
        pl.col("salario").filter(desl & sal_ok).median().alias("salario_desligamento"),
        medio.filter(adm).mean().alias("pct_medio_admitidos"),
        medio.filter(desl).mean().alias("pct_medio_desligados"),
    ]
    out = df.group_by(por).agg(exprs) if por else df.select(exprs)
    return out.with_columns(
        saldo_relativo=pl.col("saldo") / pl.col("admissoes"),
        pct_a_pedido=pl.col("desl_a_pedido") / pl.col("desligamentos") * 100,
        razao_salarial=pl.col("salario_admissao") / pl.col("salario_desligamento"),
        gap_escolaridade_pp=(pl.col("pct_medio_admitidos") - pl.col("pct_medio_desligados")) * 100,
    )


def com_populacao(tab: pl.DataFrame, pop: pl.DataFrame, coluna_regiao: str | None) -> pl.DataFrame:
    """Acrescenta população e saldo por 10 mil hab (população da região inteira)."""
    if coluna_regiao is None:
        total = int(pop["populacao_estimada_2026"].sum())
        tab = tab.with_columns(populacao=pl.lit(total, pl.Int64))
    else:
        p = pop.group_by(coluna_regiao).agg(populacao=pl.col("populacao_estimada_2026").sum())
        tab = tab.with_columns(pl.col(coluna_regiao).cast(pl.String)).join(p, on=coluna_regiao, how="left")
    return tab.with_columns(saldo_por_10mil_hab=pl.col("saldo") / pl.col("populacao") * POR_HABITANTES)


def classificar(tab: pl.DataFrame, ref: dict, min_mov: int = MIN_MOVIMENTACOES) -> pl.DataFrame:
    """Sinais de apagão e situação de cada recorte, comparados à referência estadual."""
    s_rot = pl.col("pct_a_pedido") >= ref["pct_a_pedido"] + LIMIAR_PEDIDO_PP
    s_renda = pl.col("razao_salarial") <= ref["razao_salarial"] - LIMIAR_RAZAO
    s_qualif = pl.col("gap_escolaridade_pp") <= -LIMIAR_ESCOLARIDADE_PP
    expansao = (pl.col("saldo_relativo") >= LIMIAR_EXPANSAO) & (pl.col("saldo_por_10mil_hab") >= LIMIAR_POR_10MIL)
    tab = tab.with_columns(
        sinal_rotatividade=s_rot.fill_null(False),
        sinal_renda=s_renda.fill_null(False),
        sinal_qualificacao=s_qualif.fill_null(False),
    ).with_columns(
        sinais_apagao=pl.sum_horizontal("sinal_rotatividade", "sinal_renda", "sinal_qualificacao"),
    )
    return tab.with_columns(
        situacao=pl.when(pl.col("movimentacoes") < min_mov).then(pl.lit("Volume insuficiente"))
        .when(expansao & (pl.col("sinais_apagao") >= 2)).then(pl.lit("Expansão com gargalo"))
        .when(expansao).then(pl.lit("Expansão acelerada"))
        .when(pl.col("sinais_apagao") >= 2).then(pl.lit("Sinal de apagão"))
        .when((pl.col("saldo_relativo") <= -LIMIAR_EXPANSAO)
              | (pl.col("saldo_por_10mil_hab") <= -LIMIAR_RETRACAO_10MIL)).then(pl.lit("Retração"))
        .otherwise(pl.lit("Estável")),
        causas=pl.concat_str(
            pl.when(pl.col("sinal_rotatividade")).then(pl.lit("rotatividade")),
            pl.when(pl.col("sinal_renda")).then(pl.lit("renda")),
            pl.when(pl.col("sinal_qualificacao")).then(pl.lit("qualificação")),
            separator=", ", ignore_nulls=True,
        ),
    )


def referencia(df: pl.DataFrame) -> dict:
    return agregar(df, []).row(0, named=True)


def tabela_recortes(df: pl.DataFrame, pop: pl.DataFrame, coluna_regiao: str,
                    coluna_setor: str = "polo", min_mov: int = MIN_MOVIMENTACOES) -> pl.DataFrame:
    """Região x setor classificado, pronto para o dashboard."""
    tab = agregar(df, [coluna_regiao, coluna_setor]).with_columns(pl.col(coluna_setor).cast(pl.String))
    tab = com_populacao(tab, pop, coluna_regiao)
    return classificar(tab, referencia(df), min_mov).sort("saldo", descending=True)


# --------------------------------------------------------------------------- #
# Execução
# --------------------------------------------------------------------------- #
def main() -> int:
    try:
        base = construir_base()
        ARQ_BASE.parent.mkdir(parents=True, exist_ok=True)
        tmp = ARQ_BASE.with_name(ARQ_BASE.name + ".tmp")
        base.write_parquet(tmp)
        tmp.replace(ARQ_BASE)
        pop = populacao_por_regiao()
        c = base.filter(pl.col("secao") == "C")
        tab = tabela_recortes(c, pop, "mesorregiao")
    except ErroPipeline as e:
        print(f"ERRO ({type(e).__name__}): {e}", file=sys.stderr)
        return 1
    print(f"base_dashboard.parquet: {base.height:,} linhas x {base.width} colunas")
    print("Referência SC (seção C):", {k: round(v, 3) if isinstance(v, float) else v
                                       for k, v in referencia(c).items()})
    with pl.Config(tbl_rows=50, tbl_width_chars=220, tbl_cols=12):
        print(tab.select("mesorregiao", "polo", "movimentacoes", "saldo", "saldo_por_10mil_hab",
                         "saldo_relativo", "pct_a_pedido", "razao_salarial", "gap_escolaridade_pp",
                         "situacao", "causas"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
