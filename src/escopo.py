"""Etapa 1c - Validação do escopo da pergunta de negócio.

Pergunta central (Guia do Participante, seção 2):
    "Quais regiões e setores industriais de Santa Catarina estão enfrentando
    apagão de mão de obra ou expansão acelerada, e como os indicadores de renda
    e escolaridade explicam esses gargalos?"

Este script mede se a base tratada na etapa 1 sustenta cada parte da pergunta.
Os números alimentam docs/escopo_pergunta_negocio.md.

Uso: .venv/bin/python src/escopo.py   (requer a saída de src/pipeline.py)
"""

from __future__ import annotations

import json
import sys

import polars as pl

import ingestao as ing
from erros import ErroArquivo, ErroPipeline

# Seções CNAE do "setor industrial" no conceito amplo usado pela CNI.
SECOES_INDUSTRIA_AMPLA = ["B", "C", "D", "E", "F"]

# Polos citados no guia (seção 2.1) agrupados por divisão CNAE (2 primeiros dígitos).
POLOS_INDUSTRIAIS = {
    "Agroindústria (alimentos, bebidas, fumo)": ["10", "11", "12"],
    "Têxtil, vestuário e couro": ["13", "14", "15"],
    "Metalmecânico (metalurgia, metal, máquinas, veículos, manutenção)": ["24", "25", "28", "29", "30", "33"],
    "Eletroeletrônico": ["26", "27"],
    "Madeira, papel e móveis": ["16", "17", "31"],
    "Química, plástico e minerais não metálicos": ["19", "20", "21", "22", "23"],
    "Outras (impressão, diversas)": ["18", "32"],
}
GRAUS_SUPERIOR = [9, 10, 11, 80]   # superior completo, mestrado, doutorado, pós
GRAU_MEDIO_COMPLETO = 7
TIPO_DESLIGAMENTO_A_PEDIDO = 40
SUBCLASSE_TRABALHO_TEMPORARIO = "7820500"
LIMIARES_CELULA = [30, 100, 500]


def carregar_base() -> pl.DataFrame:
    caminho = ing.DIR_PROCESSADOS / "caged_mov_tratado.parquet"
    if not caminho.exists():
        raise ErroArquivo(f"'{caminho.name}' não encontrado. Rode antes: .venv/bin/python src/pipeline.py")
    return pl.read_parquet(caminho).filter(~pl.col("flag_fora_janela"))


def fluxos() -> list[pl.Expr]:
    """Admissões, desligamentos, saldo e taxa de desligamento a pedido."""
    adm = (pl.col("saldo_movimentacao") == 1).sum()
    desl = (pl.col("saldo_movimentacao") == -1).sum()
    pedido = (pl.col("tipo_movimentacao") == TIPO_DESLIGAMENTO_A_PEDIDO).sum()
    return [
        pl.len().alias("movimentacoes"),
        adm.alias("admissoes"),
        desl.alias("desligamentos"),
        pl.col("saldo_movimentacao").sum().alias("saldo"),
        (pedido / desl).round(3).alias("pct_deslig_a_pedido"),
    ]


def perfil(df: pl.DataFrame) -> pl.DataFrame:
    """Renda e escolaridade de admitidos x desligados (salários atípicos excluídos)."""
    return (
        df.filter(~pl.col("flag_salario_atipico"))
        .group_by("movimento")
        .agg(
            pl.len().alias("n"),
            pl.col("salario").median().round(2).alias("salario_mediano"),
            pl.col("salario").mean().round(2).alias("salario_medio"),
            (pl.col("grau_instrucao") >= GRAU_MEDIO_COMPLETO).mean().round(3).alias("pct_medio_ou_mais"),
            pl.col("grau_instrucao").is_in(GRAUS_SUPERIOR).mean().round(3).alias("pct_superior"),
        )
        .sort("movimento")
    )


def validar_escopo() -> dict:
    df = carregar_base()
    total = df.height
    r: dict = {"janela": [int(df["competencia_mov"].min()), int(df["competencia_mov"].max())],
               "movimentacoes_janela": total}

    # 1. Setores: peso da indústria na base.
    secoes = df.group_by("secao").agg(fluxos()).with_columns(
        (pl.col("movimentacoes") / total).round(4).alias("pct_base")).sort("secao")
    ind_c = df.filter(pl.col("secao") == "C")
    ind_ampla = df.filter(pl.col("secao").is_in(SECOES_INDUSTRIA_AMPLA))
    r["setores"] = {
        "por_secao": secoes.to_dicts(),
        "pct_transformacao_C": round(ind_c.height / total, 4),
        "pct_industria_ampla_B_a_F": round(ind_ampla.height / total, 4),
        "saldo_C": int(ind_c["saldo_movimentacao"].sum()),
        "saldo_B_a_F": int(ind_ampla["saldo_movimentacao"].sum()),
    }

    # 2. Divisões e polos da indústria de transformação.
    ind_c = ind_c.with_columns(divisao=pl.col("subclasse").str.slice(0, 2))
    polo_por_div = {d: p for p, divs in POLOS_INDUSTRIAIS.items() for d in divs}
    sem_polo = sorted(set(ind_c["divisao"].unique()) - set(polo_por_div))
    ind_c = ind_c.with_columns(polo=pl.col("divisao").replace_strict(polo_por_div, default="Sem polo"))
    r["divisoes_C"] = ind_c.group_by("divisao").agg(fluxos()).sort("saldo").to_dicts()
    r["polos_C"] = ind_c.group_by("polo").agg(fluxos()).sort("saldo").to_dicts()
    r["divisoes_sem_polo"] = sem_polo

    # 3. "Apagão": proxies disponíveis (não há estoque nem vagas abertas no CAGED).
    desl = df.filter(pl.col("saldo_movimentacao") == -1)
    r["apagao_proxies"] = {
        "pct_deslig_a_pedido_base": round(desl.filter(pl.col("tipo_movimentacao") == TIPO_DESLIGAMENTO_A_PEDIDO).height / desl.height, 3),
        "pct_deslig_a_pedido_C": round(
            ind_c.filter(pl.col("tipo_movimentacao") == TIPO_DESLIGAMENTO_A_PEDIDO).height
            / ind_c.filter(pl.col("saldo_movimentacao") == -1).height, 3),
        "movimentacoes_trabalho_temporario_N": df.filter(pl.col("subclasse") == SUBCLASSE_TRABALHO_TEMPORARIO).height,
    }

    # 4. Renda e escolaridade.
    r["perfil_base"] = perfil(df).to_dicts()
    r["perfil_C"] = perfil(ind_c).to_dicts()
    r["qualidade_renda_escolaridade_C"] = {
        "pct_salario_atipico": round(float(ind_c["flag_salario_atipico"].mean()), 4),
        "grau_instrucao_nao_identificado": ind_c.filter(pl.col("grau_instrucao") == 99).height,
    }

    # 5. Granularidade: células município x divisão com volume suficiente.
    celulas = ind_c.group_by("municipio_codigo", "divisao").len()
    r["granularidade_mun_x_divisao_C"] = {
        "celulas": celulas.height,
        "por_limiar": [
            {"min_movimentacoes": t,
             "celulas": celulas.filter(pl.col("len") >= t).height,
             "pct_movimentacoes_cobertas": round(celulas.filter(pl.col("len") >= t)["len"].sum() / ind_c.height, 3)}
            for t in LIMIARES_CELULA
        ],
        "municipios_com_movimentacao_C": ind_c["municipio_codigo"].n_unique(),
    }

    # 6. CBOs para o agrupamento por IA.
    cbo = (ind_c.group_by("cbo2002_ocupacao").len().sort("len", descending=True)
           .with_columns(acum=pl.col("len").cum_sum() / pl.col("len").sum()))
    r["cbos_C"] = {
        "distintos": cbo.height,
        "familias_4_digitos": ind_c["cbo2002_ocupacao"].str.slice(0, 4).n_unique(),
        **{f"para_cobrir_{int(q * 100)}pct": int((cbo["acum"] < q).sum() + 1) for q in (0.8, 0.9, 0.95)},
    }

    # 7. Território: o que existe para "regiões".
    mun = pl.read_parquet(ing.DIR_PROCESSADOS / "municipios_sc.parquet")
    r["territorio"] = {
        "colunas_regionais_nos_dados": [c for c in mun.columns if "regi" in c or "meso" in c or "micro" in c],
        "populacao_disponivel": "populacao_estimada_2026" in mun.columns,
    }

    # 8. Sazonalidade mensal (afeta comparações entre meses, não o acumulado de 12 meses).
    r["saldo_mensal"] = df.group_by("competencia_mov").agg(
        pl.col("saldo_movimentacao").sum().alias("saldo")).sort("competencia_mov").to_dicts()
    return r


def main() -> int:
    try:
        r = validar_escopo()
    except ErroPipeline as e:
        print(f"ERRO ({type(e).__name__}): {e}", file=sys.stderr)
        return 1
    destino = ing.DIR_PROCESSADOS / "escopo_etapa1.json"
    destino.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k not in {"divisoes_C", "saldo_mensal"}},
                     ensure_ascii=False, indent=1))
    print(f"\nRelatório completo: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
