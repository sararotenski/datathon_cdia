"""Dashboard - Raio-X do Mercado de Trabalho Industrial em SC.

Uso (a partir da raiz do projeto):
    .venv/bin/streamlit run dashboard/app.py

Requer data/processados/base_dashboard.parquet (gerado por src/indicadores.py).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import polars as pl
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import indicadores as I  # noqa: E402

st.set_page_config(page_title="Raio-X Industrial SC", page_icon="🏭", layout="wide")

CORES_SITUACAO = {
    "Expansão com gargalo": "#d62728",
    "Expansão acelerada": "#2ca02c",
    "Sinal de apagão": "#ff7f0e",
    "Estável": "#9e9e9e",
    "Retração": "#1f77b4",
    "Volume insuficiente": "#e0e0e0",
}
ROTULO = {
    "saldo": "Saldo de vagas",
    "saldo_por_10mil_hab": "Saldo por 10 mil hab.",
    "pct_a_pedido": "% deslig. a pedido",
    "razao_salarial": "Salário admissão ÷ desligamento",
    "gap_escolaridade_pp": "Gap escolaridade (p.p.)",
    "movimentacoes": "Movimentações",
}


# --------------------------------------------------------------------------- #
# Dados
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Carregando a base…")
def carregar() -> tuple[pl.DataFrame, pl.DataFrame, dict, pl.DataFrame]:
    if not I.ARQ_BASE.exists():
        st.error("Base do dashboard não encontrada. Rode, nesta ordem: `src/pipeline.py`, "
                 "`src/integracao.py` e `src/indicadores.py`.")
        st.stop()
    base = pl.read_parquet(I.ARQ_BASE)
    pop = I.populacao_por_regiao()
    malha = orientar_malha(json.loads(I.ARQ_MALHA.read_text(encoding="utf-8")))
    desc = pl.read_csv(I.ARQ_MACROFAMILIAS, infer_schema=False).select(
        pl.col("codigo").str.zfill(6).alias("cbo2002_ocupacao"), "descricao")
    return base, pop, malha, desc


def orientar_malha(geo: dict) -> dict:
    """O Plotly (d3-geo) espera anéis externos em sentido horário; a malha do IBGE vem anti-horária."""
    def area(anel):
        return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anel, anel[1:]))

    def horario(anel, externo):
        return anel[::-1] if (area(anel) > 0) == externo else anel

    for f in geo["features"]:
        g = f["geometry"]
        poligonos = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        poligonos = [[horario(a, i == 0) for i, a in enumerate(p)] for p in poligonos]
        g["coordinates"] = poligonos[0] if g["type"] == "Polygon" else poligonos
    return geo


def fmt_int(v) -> str:
    return f"{v:+,.0f}".replace(",", ".") if v is not None else "–"


def fmt_num(v, casas=1, sinal=False) -> str:
    if v is None:
        return "–"
    s = f"{v:{'+' if sinal else ''},.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


base, pop, malha, descricoes_cbo = carregar()

# --------------------------------------------------------------------------- #
# Filtros
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Filtros")
    recorte = st.radio(
        "Recorte industrial",
        ["Indústria de transformação (C)", "Indústria ampla (B a F, inclui construção)"],
        help="A seção C contém todos os polos citados no guia. B a F é o conceito amplo da CNI.",
    )
    nivel = st.selectbox("Nível regional", list(I.NIVEIS_REGIAO)[:4], index=0)
    col_regiao = I.NIVEIS_REGIAO[nivel]

    df = base if recorte.startswith("Indústria ampla") else base.filter(pl.col("secao") == "C")
    polos_disp = sorted(df["polo"].cast(pl.String).unique().to_list())
    polos = st.multiselect("Setores / polos", polos_disp, default=polos_disp)
    if not polos:
        st.warning("Selecione ao menos um setor.")
        st.stop()
    df = df.filter(pl.col("polo").cast(pl.String).is_in(polos))

    min_mov = st.slider("Mínimo de movimentações por recorte", 100, 3000, I.MIN_MOVIMENTACOES, 100,
                        help="Recortes menores ficam como 'Volume insuficiente'.")
    st.caption("Período: competências 09/2025 a 08/2026 (Novo CAGED). "
               "População: estimativa IBGE 2026.")

ref = I.referencia(df)
tab = I.tabela_recortes(df, pop, col_regiao, "polo", min_mov)
tab_pd = tab.to_pandas()

# --------------------------------------------------------------------------- #
# Cabeçalho e KPIs
# --------------------------------------------------------------------------- #
st.title("🏭 Raio-X do Mercado de Trabalho Industrial em SC")
st.markdown(
    "> **Pergunta central:** quais regiões e setores industriais de Santa Catarina estão enfrentando "
    "**apagão de mão de obra** ou **expansão acelerada**, e como **renda e escolaridade** explicam esses gargalos?"
)

pop_sc = int(pop["populacao_estimada_2026"].sum())
k = st.columns(5)
k[0].metric("Saldo de vagas (12 meses)", fmt_int(ref["saldo"]),
            help=f"{ref['admissoes']:,} admissões − {ref['desligamentos']:,} desligamentos".replace(",", "."))
k[1].metric("Saldo por 10 mil hab.", fmt_num(ref["saldo"] / pop_sc * 1e4, 1, True))
k[2].metric("Desligamentos a pedido", f"{fmt_num(ref['pct_a_pedido'])}%",
            help="Trabalhador que pede demissão: indicador de disputa por mão de obra.")
k[3].metric("Salário admissão ÷ desligamento", fmt_num(ref["razao_salarial"], 2),
            delta=f"{fmt_num((ref['razao_salarial'] - 1) * 100, 1, True)}%", delta_color="normal",
            help=f"Mediana: R$ {fmt_num(ref['salario_admissao'], 0)} (admitidos) x "
                 f"R$ {fmt_num(ref['salario_desligamento'], 0)} (desligados).")
k[4].metric("Gap de escolaridade", f"{fmt_num(ref['gap_escolaridade_pp'], 1, True)} p.p.",
            help="% de admitidos com médio completo ou mais, menos o mesmo % entre os desligados.")

contagem = tab.group_by("situacao").len()
criticos = tab.filter(pl.col("situacao").is_in(["Expansão com gargalo", "Sinal de apagão"])).height
st.info(f"**{criticos}** recorte(s) região × setor com sinal de apagão e "
        f"**{tab.filter(pl.col('situacao') == 'Retração').height}** em retração, "
        f"num total de {tab.height} analisados ({nivel.lower()} × setor).")

aba1, aba2, aba3, aba4, aba5 = st.tabs(
    ["📍 Onde está o problema", "🔎 Causa raiz", "👷 Ocupações (CBO)", "✅ Recomendações", "📐 Metodologia"])

# --------------------------------------------------------------------------- #
# 1. Onde
# --------------------------------------------------------------------------- #
with aba1:
    esq, dir_ = st.columns([1.1, 1])
    with esq:
        st.subheader("Mapa por município")
        opcoes_mapa = {ROTULO[c]: c for c in
                       ["saldo_por_10mil_hab", "pct_a_pedido", "razao_salarial", "gap_escolaridade_pp"]}
        metrica_mapa = opcoes_mapa[st.selectbox("Indicador do mapa", list(opcoes_mapa))]
        mun = I.com_populacao(I.agregar(df, ["municipio_nome"]), pop, "municipio_nome") \
            .join(pop.select("municipio_nome", "codigo_ibge", col_regiao) if col_regiao != "municipio_nome"
                  else pop.select("municipio_nome", "codigo_ibge"), on="municipio_nome", how="left")
        mun = mun.with_columns(
            valor=pl.when(pl.col("movimentacoes") >= 30).then(pl.col(metrica_mapa)))
        mun_pd = mun.to_pandas()
        lim = float(mun_pd["valor"].abs().quantile(0.95) or 1)
        centro = {"razao_salarial": 1.0}.get(metrica_mapa, 0.0)
        escala = "RdBu" if metrica_mapa != "pct_a_pedido" else "OrRd"
        fig = px.choropleth(
            mun_pd, geojson=malha, locations="codigo_ibge", featureidkey="properties.codarea",
            color="valor", color_continuous_scale=escala,
            range_color=None if metrica_mapa in ("pct_a_pedido", "razao_salarial")
            else (-lim, lim),
            color_continuous_midpoint=centro if metrica_mapa != "pct_a_pedido" else None,
            hover_name="municipio_nome",
            hover_data={"codigo_ibge": False, "valor": False, "saldo": True, "movimentacoes": True,
                        "saldo_por_10mil_hab": ":.1f", "pct_a_pedido": ":.1f", "razao_salarial": ":.2f"},
            labels={**ROTULO, "valor": ROTULO[metrica_mapa]},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430,
                          coloraxis_colorbar=dict(title=ROTULO[metrica_mapa], len=0.7))
        st.plotly_chart(fig, config={"displayModeBar": False})
        st.caption("Municípios com menos de 30 movimentações no recorte ficam sem cor.")

    with dir_:
        st.subheader(f"Matriz {nivel.lower()} × setor")
        mat = tab_pd.pivot_table(index=col_regiao, columns="polo", values="saldo_por_10mil_hab", aggfunc="first")
        sit = tab_pd.pivot_table(index=col_regiao, columns="polo", values="situacao", aggfunc="first")
        texto = sit.map(lambda s: {"Expansão com gargalo": "⚠️↑", "Expansão acelerada": "↑",
                                   "Sinal de apagão": "⚠️", "Retração": "↓",
                                   "Volume insuficiente": "·"}.get(s, "") if isinstance(s, str) else "")
        lim2 = float(abs(mat.stack()).quantile(0.95) or 1)
        hm = go.Figure(go.Heatmap(
            z=mat.values, x=mat.columns, y=mat.index, text=texto.values, texttemplate="%{text}",
            colorscale="RdBu", zmid=0, zmin=-lim2, zmax=lim2,
            customdata=sit.values,
            hovertemplate="%{y} · %{x}<br>Saldo por 10 mil hab: %{z:.1f}<br>%{customdata}<extra></extra>",
            colorbar=dict(title="Saldo/10 mil"),
        ))
        hm.update_layout(height=430 + max(0, 18 * (len(mat) - 8)), margin=dict(l=0, r=0, t=10, b=0),
                         xaxis_tickangle=-30)
        st.plotly_chart(hm, config={"displayModeBar": False})
        st.caption("↑ expansão acelerada · ⚠️↑ expansão com gargalo · ⚠️ sinal de apagão · ↓ retração · "
                   "· volume insuficiente")

    st.subheader("Recortes que pedem atenção")
    foco = tab.filter(pl.col("situacao").is_in(["Expansão com gargalo", "Sinal de apagão",
                                                "Expansão acelerada", "Retração"]))
    st.dataframe(
        foco.select(col_regiao, "polo", "situacao", "causas", "saldo", "saldo_por_10mil_hab",
                    "pct_a_pedido", "razao_salarial", "gap_escolaridade_pp", "movimentacoes").to_pandas(),
        hide_index=True,
        column_config={
            col_regiao: nivel, "polo": "Setor", "situacao": "Situação", "causas": "Sinais de apagão",
            "saldo": st.column_config.NumberColumn("Saldo", format="%+d"),
            "saldo_por_10mil_hab": st.column_config.NumberColumn("Saldo/10 mil hab", format="%+.1f"),
            "pct_a_pedido": st.column_config.NumberColumn("% a pedido", format="%.1f"),
            "razao_salarial": st.column_config.NumberColumn("Sal. adm ÷ desl", format="%.2f"),
            "gap_escolaridade_pp": st.column_config.NumberColumn("Gap escol. (p.p.)", format="%+.1f"),
            "movimentacoes": st.column_config.NumberColumn("Movimentações", format="%d"),
        },
    )

# --------------------------------------------------------------------------- #
# 2. Causa raiz
# --------------------------------------------------------------------------- #
with aba2:
    st.subheader("Expansão × rotatividade")
    validos = tab_pd[tab_pd["situacao"] != "Volume insuficiente"]
    sc = px.scatter(
        validos, x="saldo_por_10mil_hab", y="pct_a_pedido", size="movimentacoes", color="situacao",
        color_discrete_map=CORES_SITUACAO, hover_name=col_regiao,
        hover_data={"polo": True, "saldo": True, "razao_salarial": ":.2f", "gap_escolaridade_pp": ":.1f"},
        labels={**ROTULO, "situacao": "Situação", "polo": "Setor"}, size_max=45,
        category_orders={"situacao": I.ORDEM_SITUACAO},
    )
    sc.add_hline(y=ref["pct_a_pedido"], line_dash="dot", annotation_text="média SC")
    sc.add_vline(x=0, line_dash="dot")
    sc.update_layout(height=480, margin=dict(t=20))
    st.plotly_chart(sc)
    st.caption("Acima da linha pontilhada: trabalhadores pedindo demissão mais que a média estadual "
               "(mercado disputado). À direita: o recorte cria vagas.")

    st.subheader("Diagnóstico de um recorte")
    opcoes = validos.sort_values("saldo", ascending=False)
    rotulos = (opcoes[col_regiao] + " · " + opcoes["polo"]).tolist()
    if rotulos:
        escolha = st.selectbox("Escolha região × setor", rotulos,
                               key=f"diag_{col_regiao}_{recorte}_{'|'.join(polos)}_{min_mov}")
        linha = opcoes.iloc[rotulos.index(escolha)]
        sel = df.filter((pl.col(col_regiao).cast(pl.String) == linha[col_regiao])
                        & (pl.col("polo").cast(pl.String) == linha["polo"]))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Situação", linha["situacao"])
        c2.metric("% a pedido", f"{fmt_num(linha['pct_a_pedido'])}%",
                  delta=f"{fmt_num(linha['pct_a_pedido'] - ref['pct_a_pedido'], 1, True)} p.p. vs SC",
                  delta_color="inverse")
        c3.metric("Salário adm ÷ desl", fmt_num(linha["razao_salarial"], 2),
                  delta=f"{fmt_num(linha['razao_salarial'] - ref['razao_salarial'], 2, True)} vs SC")
        c4.metric("Gap escolaridade", f"{fmt_num(linha['gap_escolaridade_pp'], 1, True)} p.p.")

        g1, g2 = st.columns(2)
        with g1:
            esc = (sel.with_columns(
                movimento=pl.when(pl.col("saldo_movimentacao") == 1).then(pl.lit("Admitidos")).otherwise(pl.lit("Desligados")),
                escolaridade=pl.when(pl.col("grau_instrucao") <= 5).then(pl.lit("Até fundamental"))
                .when(pl.col("grau_instrucao") <= 6).then(pl.lit("Médio incompleto"))
                .when(pl.col("grau_instrucao") <= 8).then(pl.lit("Médio completo / sup. incompleto"))
                .otherwise(pl.lit("Superior ou mais")))
                .group_by("movimento", "escolaridade").len()
                .with_columns(pct=pl.col("len") / pl.col("len").sum().over("movimento") * 100))
            fe = px.bar(esc.to_pandas(), x="escolaridade", y="pct", color="movimento", barmode="group",
                        category_orders={"escolaridade": ["Até fundamental", "Médio incompleto",
                                                          "Médio completo / sup. incompleto", "Superior ou mais"]},
                        labels={"pct": "% do grupo", "escolaridade": "", "movimento": ""},
                        title="Escolaridade: admitidos x desligados")
            fe.update_layout(height=360)
            st.plotly_chart(fe)
        with g2:
            sal = (sel.filter(~pl.col("flag_salario_atipico"))
                   .with_columns(movimento=pl.when(pl.col("saldo_movimentacao") == 1).then(pl.lit("Admitidos"))
                                 .otherwise(pl.lit("Desligados")))
                   .group_by("movimento", "nivel_qualificacao")
                   .agg(salario=pl.col("salario").median()))
            fs = px.bar(sal.to_pandas(), x="nivel_qualificacao", y="salario", color="movimento", barmode="group",
                        labels={"salario": "Salário mediano (R$)", "nivel_qualificacao": "", "movimento": ""},
                        title="Salário mediano por nível de ocupação")
            fs.update_layout(height=360)
            st.plotly_chart(fs)

# --------------------------------------------------------------------------- #
# 3. Ocupações
# --------------------------------------------------------------------------- #
with aba3:
    st.subheader("Que tipo de profissional está em falta ou sobrando?")
    st.caption("Ocupações agrupadas nas 20 macrofamílias da etapa de IA "
               "(cbo_macrofamilia.csv; método em docs/metodologia_ia_cbo.md).")
    regs = ["Santa Catarina (todas)"] + sorted(df[col_regiao].cast(pl.String).unique().to_list())
    reg = st.selectbox(nivel, regs, key=f"ocup_{col_regiao}_{recorte}_{'|'.join(polos)}")
    d3 = df if reg == regs[0] else df.filter(pl.col(col_regiao).cast(pl.String) == reg)
    ref3 = I.referencia(d3)
    occ = I.agregar(d3, ["macrofamilia_cbo"]).with_columns(
        pl.col("macrofamilia_cbo").cast(pl.String)).filter(pl.col("movimentacoes") >= 100).sort("saldo")
    o1, o2 = st.columns(2)
    with o1:
        fb = px.bar(occ.to_pandas(), x="saldo", y="macrofamilia_cbo", orientation="h",
                    color="pct_a_pedido", color_continuous_scale="OrRd",
                    hover_data={"movimentacoes": True, "salario_admissao": ":.0f", "gap_escolaridade_pp": ":.1f"},
                    labels={"saldo": "Saldo de vagas", "macrofamilia_cbo": "", "pct_a_pedido": "% a pedido",
                            **ROTULO, "salario_admissao": "Sal. admissão"},
                    title="Saldo por macrofamília (cor: % de desligamentos a pedido)")
        fb.update_layout(height=560, coloraxis_colorbar=dict(orientation="h", y=-0.18, len=0.6,
                                                              thickness=12, title_side="top"))
        st.plotly_chart(fb)
    with o2:
        fr = px.scatter(occ.to_pandas(), x="gap_escolaridade_pp", y="razao_salarial", size="movimentacoes",
                        color="saldo", color_continuous_scale="RdBu", color_continuous_midpoint=0,
                        hover_name="macrofamilia_cbo",
                        hover_data={"saldo": True, "pct_a_pedido": ":.1f", "salario_admissao": ":.0f"},
                        labels={**ROTULO, "salario_admissao": "Sal. admissão"}, size_max=45,
                        title="Renda × escolaridade de quem entra vs quem sai")
        fr.add_hline(y=1, line_dash="dot")
        fr.add_vline(x=0, line_dash="dot")
        fr.update_layout(height=560)
        st.plotly_chart(fr)
    st.caption("No gráfico da direita, quanto mais à esquerda, menor a escolaridade dos admitidos em relação "
               "aos desligados; abaixo de 1, a reposição paga menos que o salário de quem sai.")

    top = (I.agregar(d3, ["cbo2002_ocupacao", "macrofamilia_cbo"]).filter(pl.col("movimentacoes") >= 200)
           .join(descricoes_cbo, on="cbo2002_ocupacao", how="left").sort("saldo"))
    a, b = st.columns(2)
    cfg = {"cbo2002_ocupacao": "CBO", "descricao": "Ocupação", "macrofamilia_cbo": "Macrofamília", "saldo": st.column_config.NumberColumn("Saldo", format="%+d"),
           "pct_a_pedido": st.column_config.NumberColumn("% a pedido", format="%.1f"),
           "salario_admissao": st.column_config.NumberColumn("Sal. admissão", format="R$ %.0f")}
    sel_cols = ["descricao", "macrofamilia_cbo", "saldo", "pct_a_pedido", "salario_admissao"]
    a.markdown("**CBOs que mais cresceram**")
    a.dataframe(top.tail(10).reverse().select(sel_cols).to_pandas(), hide_index=True, column_config=cfg)
    b.markdown("**CBOs que mais encolheram**")
    b.dataframe(top.head(10).select(sel_cols).to_pandas(), hide_index=True, column_config=cfg)

# --------------------------------------------------------------------------- #
# 4. Recomendações
# --------------------------------------------------------------------------- #
ACOES = {
    "rotatividade": "**Retenção**: desligamentos a pedido acima da média. Plano de carreira, benefícios "
                    "e programas de integração para os primeiros meses.",
    "renda": "**Revisão salarial**: a reposição paga menos que o salário de quem sai, "
             "o que dificulta atrair candidatos. Rever as faixas de admissão.",
    "qualificação": "**Formação direcionada**: as vagas estão sendo preenchidas com escolaridade menor "
                    "que a de quem sai. Cursos técnicos e de elevação de escolaridade (ex.: SENAI/IFSC) "
                    "com as empresas da região.",
}
with aba4:
    st.subheader("Recomendações por recorte")
    st.caption("Geradas a partir dos sinais de cada recorte com os filtros atuais.")
    for _, r in tab_pd[tab_pd["situacao"].isin(["Expansão com gargalo", "Sinal de apagão"])].iterrows():
        with st.container(border=True):
            st.markdown(f"#### ⚠️ {r[col_regiao]} · {r['polo']} — {r['situacao']}")
            st.markdown(f"Saldo **{fmt_int(r['saldo'])}** ({fmt_num(r['saldo_por_10mil_hab'], 1, True)} por 10 mil hab), "
                        f"{fmt_num(r['pct_a_pedido'])}% dos desligamentos a pedido, salário de admissão "
                        f"{fmt_num((r['razao_salarial'] - 1) * 100, 1, True)}% em relação ao de desligamento, "
                        f"gap de escolaridade {fmt_num(r['gap_escolaridade_pp'], 1, True)} p.p.")
            for causa in (r["causas"] or "").split(", "):
                if causa in ACOES:
                    st.markdown(f"- {ACOES[causa]}")
            cel = df.filter((pl.col(col_regiao).cast(pl.String) == r[col_regiao])
                            & (pl.col("polo").cast(pl.String) == r["polo"]))
            mf = I.agregar(cel, ["macrofamilia_cbo"]).filter(pl.col("movimentacoes") >= 200)
            cresce = mf.filter(pl.col("saldo") > 0).sort("saldo", descending=True).head(3)
            if cresce.height:
                st.markdown("- **Onde focar** (macrofamílias que mais contratam no recorte): " + "; ".join(
                    f"{m['macrofamilia_cbo']} ({fmt_int(m['saldo'])}, {fmt_num(m['pct_a_pedido'])}% a pedido, "
                    f"gap {fmt_num(m['gap_escolaridade_pp'], 1, True)} p.p.)" for m in cresce.iter_rows(named=True)))
    retr = tab_pd[tab_pd["situacao"] == "Retração"]
    if len(retr):
        with st.container(border=True):
            st.markdown("#### ↓ Setores em retração")
            st.markdown(", ".join(f"{r[col_regiao]} · {r['polo']} ({fmt_int(r['saldo'])})" for _, r in retr.iterrows()))
            st.markdown("- **Requalificação e recolocação**: trabalhadores desligados destes setores podem ser "
                        "direcionados, com formação curta, aos polos em expansão da mesma região.")
    exp = tab_pd[tab_pd["situacao"] == "Expansão acelerada"]
    if len(exp):
        with st.container(border=True):
            st.markdown("#### ↑ Expansão sem gargalo aparente")
            st.markdown(", ".join(f"{r[col_regiao]} · {r['polo']} ({fmt_int(r['saldo'])})" for _, r in exp.iterrows()))
            st.markdown("- **Antecipar demanda**: acompanhar infraestrutura local e formação antes que a "
                        "expansão vire escassez.")

# --------------------------------------------------------------------------- #
# 5. Metodologia
# --------------------------------------------------------------------------- #
with aba5:
    st.markdown(f"""
**Fontes**
- Novo CAGED (MTE), Santa Catarina, competências 09/2025 a 08/2026: {base.height:,} movimentações da indústria (B a F).
- IBGE: população estimada 2026, regiões geográficas (API de localidades) e malha municipal (API de malhas).

**Indicadores** (calculados para cada região × setor e comparados com a média do recorte em SC)
- *Saldo por 10 mil hab.* = (admissões − desligamentos) ÷ população da região × 10.000.
- *Saldo relativo* = saldo ÷ admissões.
- *% desligamentos a pedido*: tipo de movimentação 40.
- *Razão salarial* = salário mediano de admissão ÷ salário mediano de desligamento (sem salários fora de 0,3–150 salários mínimos).
- *Gap de escolaridade* = % de admitidos com médio completo ou mais − mesmo % entre desligados.

**Classificação**
- *Expansão acelerada*: saldo relativo ≥ {I.LIMIAR_EXPANSAO:.0%} e saldo ≥ {I.LIMIAR_POR_10MIL:g} por 10 mil hab.
- *Sinais de apagão*: rotatividade (% a pedido ≥ média + {I.LIMIAR_PEDIDO_PP:g} p.p.), renda (razão ≤ média − {I.LIMIAR_RAZAO}) e qualificação (gap ≤ −{I.LIMIAR_ESCOLARIDADE_PP:g} p.p.). Dois ou mais = *sinal de apagão*; com expansão = *expansão com gargalo*.
- *Retração*: saldo relativo ≤ −{I.LIMIAR_EXPANSAO:.0%} ou ≤ −{I.LIMIAR_RETRACAO_10MIL:g} por 10 mil hab.

**Limites da análise**
1. O CAGED não tem vagas abertas nem estoque de empregos: o apagão é medido por sinais indiretos.
2. Exclusões (arquivos CAGEDEXC do MTE) não aplicadas; efeito medido de +90 no saldo de SC.
3. Trabalho temporário (subclasse 7820500) fica na seção N, fora da indústria, mesmo quando o trabalhador atua nela.
4. Microdados sem identificador: não dá para seguir a trajetória de cada trabalhador.
5. Macrofamílias de CBO definidas com apoio de IA e regras; concordância de 85% por CBO e 97,5% ponderada por movimentações na amostra de validação (docs/metodologia_ia_cbo.md).
""")
