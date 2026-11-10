"""Etapa 2 - Cruzamento relacional: CAGED x IBGE e saldo por 10 mil habitantes.

1. Junta as movimentações tratadas (etapa 1) com os dados dos municípios pela
   chave ``municipio_codigo`` (6 dígitos), garantindo relação N:1 sem perda.
2. Calcula, por município, o saldo de vagas por 10.000 habitantes:

       saldo_por_10mil_hab = saldo_12m / populacao_estimada_2026 * 10.000

   - saldo_12m: admissões - desligamentos com competência de 09/2025 a 08/2026
     (declarações atrasadas de meses anteriores ficam de fora: flag_fora_janela).
   - população: estimativa IBGE 2026, a mais próxima da janela analisada.
   Calculado para o total de setores e para a indústria de transformação (seção C).

Uso: .venv/bin/python src/integracao.py   (requer a saída de src/pipeline.py)

Saídas em data/processados/:
    caged_territorial.parquet     movimentações + atributos do município (linha a linha)
    saldo_municipio.parquet/.csv  uma linha por município com a métrica
"""

from __future__ import annotations

import json
import sys

import polars as pl

import erros
import ingestao as ing
from erros import ErroArquivo, ErroPipeline, ErroSchema, ErroValidacao
from pipeline import gravar_atomico, titulo

CHAVE = "municipio_codigo"
POR_HABITANTES = 10_000
COL_POPULACAO = "populacao_estimada_2026"
SECAO_INDUSTRIA = "C"
# Abaixo disso, o indicador do município oscila muito com poucas contratações.
MIN_MOVIMENTACOES = 30


def carregar(nome: str) -> pl.DataFrame:
    caminho = ing.DIR_PROCESSADOS / nome
    if not caminho.exists():
        raise ErroArquivo(f"'{nome}' não encontrado. Rode antes: .venv/bin/python src/pipeline.py")
    try:
        return pl.read_parquet(caminho)
    except pl.exceptions.PolarsError as e:
        raise ErroArquivo(f"'{nome}' está corrompido; rode src/pipeline.py de novo. {e}") from e


def validar_chave(caged: pl.DataFrame, mun: pl.DataFrame) -> dict:
    """Mesmo tipo e formato dos dois lados, chave única no IBGE e cobertura total."""
    for nome, df in (("CAGED", caged), ("Municípios", mun)):
        if CHAVE not in df.columns:
            raise ErroSchema(f"{nome}: coluna '{CHAVE}' ausente.")
        if df.schema[CHAVE] != pl.String:
            raise ErroSchema(f"{nome}: '{CHAVE}' deveria ser texto, é {df.schema[CHAVE]}.")
        fora_formato = df.filter(~pl.col(CHAVE).str.contains(r"^42\d{4}$") | pl.col(CHAVE).is_null())
        if fora_formato.height:
            raise ErroValidacao(
                f"{nome}: {fora_formato.height:,} chave(s) fora do formato 42xxxx: "
                f"{fora_formato[CHAVE].unique().head(5).to_list()}"
            )
    if COL_POPULACAO not in mun.columns:
        raise ErroSchema(f"Municípios: coluna '{COL_POPULACAO}' ausente.")

    repetidas = mun.filter(pl.col(CHAVE).is_duplicated())[CHAVE].unique().to_list()
    if repetidas:
        raise ErroValidacao(f"Municípios: chave repetida (duplicaria linhas no join): {repetidas}")

    sem_ibge = sorted(set(caged[CHAVE].unique()) - set(mun[CHAVE]))
    if sem_ibge:
        raise ErroValidacao(f"CAGED: {len(sem_ibge)} município(s) sem correspondência no IBGE: {sem_ibge[:10]}")
    sem_caged = sorted(set(mun[CHAVE]) - set(caged[CHAVE].unique()))
    if sem_caged:
        erros.avisar(f"Municípios sem movimentação no CAGED (saldo 0): {sem_caged}")
    return {"municipios_caged": caged[CHAVE].n_unique(), "municipios_ibge": mun.height,
            "ibge_sem_caged": sem_caged}


def juntar(caged: pl.DataFrame, mun: pl.DataFrame) -> pl.DataFrame:
    """Left join N:1. Falha se o número de linhas mudar ou sobrar município sem atributos."""
    conflito = (set(caged.columns) & set(mun.columns)) - {CHAVE}
    if conflito:
        raise ErroSchema(f"Colunas com o mesmo nome nas duas bases: {sorted(conflito)}")
    try:
        df = caged.join(mun, on=CHAVE, how="left", validate="m:1")
    except pl.exceptions.ComputeError as e:
        raise ErroValidacao(f"Join CAGED x IBGE não é N:1. {e}") from e

    if df.height != caged.height:
        raise ErroValidacao(f"Join alterou o nº de linhas: {caged.height:,} -> {df.height:,}")
    sem_nome = df.filter(pl.col("municipio_nome").is_null()).height
    if sem_nome:
        raise ErroValidacao(f"{sem_nome:,} linha(s) ficaram sem atributos do município após o join.")
    return df


def saldo_por_municipio(df: pl.DataFrame, mun: pl.DataFrame) -> pl.DataFrame:
    """Uma linha por município (inclusive os sem movimentação) com saldos e a métrica."""
    janela = df.filter(~pl.col("flag_fora_janela"))
    eh_ind = pl.col("secao") == SECAO_INDUSTRIA
    adm = pl.col("saldo_movimentacao") == 1
    desl = pl.col("saldo_movimentacao") == -1

    agregado = janela.group_by(CHAVE).agg(
        movimentacoes=pl.len(),
        admissoes=adm.sum(),
        desligamentos=desl.sum(),
        saldo=pl.col("saldo_movimentacao").sum(),
        movimentacoes_industria=eh_ind.sum(),
        admissoes_industria=(adm & eh_ind).sum(),
        desligamentos_industria=(desl & eh_ind).sum(),
        saldo_industria=pl.col("saldo_movimentacao").filter(eh_ind).sum(),
    )
    contagens = [c for c in agregado.columns if c != CHAVE]
    pop = pl.col(COL_POPULACAO)
    return (
        mun.select(CHAVE, "municipio_nome", "codigo_ibge", COL_POPULACAO)
        .join(agregado, on=CHAVE, how="left", validate="1:1")
        .with_columns(pl.col(contagens).fill_null(0).cast(pl.Int64))
        .with_columns(
            saldo_por_10mil_hab=(pl.col("saldo") / pop * POR_HABITANTES).round(2),
            saldo_industria_por_10mil_hab=(pl.col("saldo_industria") / pop * POR_HABITANTES).round(2),
            flag_baixo_volume=pl.col("movimentacoes") < MIN_MOVIMENTACOES,
            flag_baixo_volume_industria=pl.col("movimentacoes_industria") < MIN_MOVIMENTACOES,
        )
        .sort("saldo_por_10mil_hab", descending=True)
    )


def conferir_metrica(ind: pl.DataFrame, df: pl.DataFrame) -> dict:
    """A soma dos municípios precisa bater com o total da base."""
    janela = df.filter(~pl.col("flag_fora_janela"))
    esperado = int(janela["saldo_movimentacao"].sum())
    esperado_ind = int(janela.filter(pl.col("secao") == SECAO_INDUSTRIA)["saldo_movimentacao"].sum())
    obtido, obtido_ind = int(ind["saldo"].sum()), int(ind["saldo_industria"].sum())
    if (obtido, obtido_ind) != (esperado, esperado_ind):
        raise ErroValidacao(
            f"Soma dos municípios não bate com a base: saldo {obtido} x {esperado}, "
            f"indústria {obtido_ind} x {esperado_ind}"
        )
    if ind["saldo_por_10mil_hab"].is_null().any() or ind["saldo_por_10mil_hab"].is_infinite().any():
        raise ErroValidacao("Métrica com valor nulo/infinito (população ausente ou zero?).")
    pop_sc = int(ind[COL_POPULACAO].sum())
    return {
        "saldo_sc": esperado,
        "saldo_industria_sc": esperado_ind,
        "populacao_sc_2026": pop_sc,
        "saldo_por_10mil_hab_sc": round(esperado / pop_sc * POR_HABITANTES, 2),
        "saldo_industria_por_10mil_hab_sc": round(esperado_ind / pop_sc * POR_HABITANTES, 2),
    }


def etapa_2() -> dict:
    erros.AVISOS.clear()
    rel: dict = {}

    titulo("1. Carga das bases da etapa 1")
    caged = carregar("caged_mov_tratado.parquet")
    mun = carregar("municipios_sc.parquet")
    print(f"CAGED: {caged.height:,} linhas | Municípios: {mun.height}")

    titulo("2. Validação da chave municipio_codigo")
    rel["chave"] = validar_chave(caged, mun)
    print(rel["chave"])

    titulo("3. Join CAGED x IBGE (left, N:1)")
    df = juntar(caged, mun)
    del caged
    print(f"Resultado: {df.height:,} linhas x {df.width} colunas (nenhuma linha perdida ou duplicada)")

    titulo("4. Saldo de vagas por 10.000 habitantes")
    ind = saldo_por_municipio(df, mun)
    rel["estado"] = conferir_metrica(ind, df)
    print(rel["estado"])
    cols = ["municipio_nome", COL_POPULACAO, "saldo", "saldo_por_10mil_hab",
            "saldo_industria", "saldo_industria_por_10mil_hab"]
    confiaveis = ind.filter(~pl.col("flag_baixo_volume"))
    with pl.Config(tbl_rows=10, tbl_width_chars=160, tbl_formatting="ASCII_MARKDOWN"):
        print("\nMaiores saldos por 10 mil hab:")
        print(confiaveis.head(10).select(cols))
        print("\nMenores saldos por 10 mil hab:")
        print(confiaveis.tail(10).select(cols))
    rel["municipios_baixo_volume"] = int(ind["flag_baixo_volume"].sum())
    rel["municipios_baixo_volume_industria"] = int(ind["flag_baixo_volume_industria"].sum())
    print(f"\nMunicípios com < {MIN_MOVIMENTACOES} movimentações: total {rel['municipios_baixo_volume']}, "
          f"indústria {rel['municipios_baixo_volume_industria']}")

    titulo("5. Exportação")
    gravar_atomico(ing.DIR_PROCESSADOS / "caged_territorial.parquet", df.write_parquet)
    gravar_atomico(ing.DIR_PROCESSADOS / "saldo_municipio.parquet", ind.write_parquet)
    gravar_atomico(ing.DIR_PROCESSADOS / "saldo_municipio.csv", ind.write_csv)
    rel["avisos"] = list(erros.AVISOS)

    def escrever_json(caminho):
        caminho.write_text(json.dumps(rel, ensure_ascii=False, indent=2), encoding="utf-8")

    gravar_atomico(ing.DIR_PROCESSADOS / "relatorio_etapa2.json", escrever_json)
    print(f"caged_territorial.parquet: {df.height:,} x {df.width} | saldo_municipio: {ind.height} municípios")
    return rel


def main() -> int:
    try:
        etapa_2()
    except ErroPipeline as e:
        print(f"\nERRO ({type(e).__name__}): {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
