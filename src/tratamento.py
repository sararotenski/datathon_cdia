"""Etapa 1b - Tratamento de inconsistências e filtragem das exclusões (MOV x EXC).

Princípio: nenhuma linha válida é descartada sem regra explícita. Problemas que
não invalidam a movimentação (salário atípico, CBO fora do dicionário, idade
ausente) viram *flags*, para que cada indicador decida como tratá-los.

Tratamento de erros:
- ``ErroConversao``: valor não vazio que não converte para o tipo esperado.
  A conversão nunca transforma lixo em nulo silenciosamente.
- ``ErroValidacao``: regra crítica violada (o resultado ficaria errado).
- ``avisar``: inconsistência que não impede a análise; vai para o relatório.
"""

from __future__ import annotations

import pandas as pd
import polars as pl

from erros import ErroConversao, ErroSchema, ErroValidacao, avisar

# --------------------------------------------------------------------------- #
# Constantes
# --------------------------------------------------------------------------- #
# Nomes do layout (com acento) -> snake_case sem acento.
RENOMEAR_CAGED = {
    "competênciamov": "competencia_mov",
    "região": "regiao",
    "uf": "uf",
    "município": "municipio_codigo",
    "seção": "secao",
    "subclasse": "subclasse",
    "saldomovimentação": "saldo_movimentacao",
    "cbo2002ocupação": "cbo2002_ocupacao",
    "categoria": "categoria",
    "graudeinstrução": "grau_instrucao",
    "idade": "idade",
    "horascontratuais": "horas_contratuais",
    "raçacor": "raca_cor",
    "sexo": "sexo",
    "tipoempregador": "tipo_empregador",
    "tipoestabelecimento": "tipo_estabelecimento",
    "tipomovimentação": "tipo_movimentacao",
    "tipodedeficiência": "tipo_deficiencia",
    "indtrabintermitente": "ind_trab_intermitente",
    "indtrabparcial": "ind_trab_parcial",
    "salário": "salario",
    "tamestabjan": "tam_estab_jan",
    "indicadoraprendiz": "indicador_aprendiz",
    "origemdainformação": "origem_informacao",
    "competênciadec": "competencia_dec",
    "competênciaexc": "competencia_exc",
    "indicadordeexclusão": "indicador_exclusao",
    "indicadordeforadoprazo": "indicador_fora_prazo",
    "unidadesaláriocódigo": "unidade_salario_codigo",
    "valorsaláriofixo": "valor_salario_fixo",
}

COLS_DECIMAL_VIRGULA = ["salario", "horas_contratuais", "valor_salario_fixo"]
COLS_CODIGO_INTEIRO = [
    "regiao", "uf", "saldo_movimentacao", "categoria", "grau_instrucao", "raca_cor",
    "sexo", "tipo_empregador", "tipo_estabelecimento", "tipo_movimentacao",
    "tipo_deficiencia", "ind_trab_intermitente", "ind_trab_parcial", "tam_estab_jan",
    "indicador_aprendiz", "origem_informacao", "indicador_fora_prazo",
    "unidade_salario_codigo", "indicador_exclusao",
]
COLS_COMPETENCIA = ["competencia_mov", "competencia_dec", "competencia_exc"]
# Códigos textuais com largura fixa (zeros à esquerda importam).
COLS_CODIGO_TEXTO = {"municipio_codigo": 6, "cbo2002_ocupacao": 6, "subclasse": 7}

# Sem estas colunas preenchidas não há saldo, território, setor nem salário.
COLS_CRITICAS = [
    "competencia_mov", "competencia_dec", "municipio_codigo", "secao", "subclasse",
    "saldo_movimentacao", "cbo2002_ocupacao", "salario", "grau_instrucao",
]
TIPOS_ADMISSAO = [10, 20, 25, 35, 70, 97]
TIPOS_DESLIGAMENTO = [31, 32, 33, 40, 43, 45, 50, 60, 80, 90, 98]
FAIXA_IDADE_PLAUSIVEL = (14, 100)

# Salário mínimo nacional por ano (Decretos 11.864/2023, 12.342/2024, 12.797/2025).
SALARIO_MINIMO = {2024: 1412.00, 2025: 1518.00, 2026: 1621.00}
# Faixa de salário considerada válida para médias salariais, em salários mínimos.
FAIXA_SALARIO_SM = (0.3, 150.0)


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #
def exigir_colunas(df: pl.DataFrame | pd.DataFrame, colunas, contexto: str) -> None:
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise ErroSchema(f"{contexto}: colunas obrigatórias ausentes: {faltando}")


def _converter(
    df: pl.DataFrame, conversoes: dict[str, tuple[pl.Expr, str]], arquivo: str
) -> pl.DataFrame:
    """Aplica conversões e falha se algum valor não nulo virar nulo.

    ``conversoes``: coluna -> (expressão de conversão não estrita, tipo esperado).
    """
    if not conversoes:
        return df
    tmp = df.with_columns([expr.alias(f"__{c}") for c, (expr, _) in conversoes.items()])
    falhou = {c: pl.col(c).is_not_null() & pl.col(f"__{c}").is_null() for c in conversoes}
    contagens = tmp.select([f.sum().alias(c) for c, f in falhou.items()]).row(0, named=True)

    for c, n in contagens.items():
        if n:
            exemplos = (
                tmp.filter(falhou[c]).get_column(c).value_counts(sort=True).get_column(c).head(5).to_list()
            )
            raise ErroConversao(arquivo, c, n, exemplos, conversoes[c][1])

    return (
        tmp.drop(list(conversoes))
        .rename({f"__{c}": c for c in conversoes})
        .select(df.columns)
    )


# --------------------------------------------------------------------------- #
# CAGED
# --------------------------------------------------------------------------- #
def padronizar_caged(df: pl.DataFrame, arquivo: str = "CAGED") -> pl.DataFrame:
    """Remove colunas de índice, renomeia e converte tipos.

    Funciona tanto para o arquivo MOV quanto para o EXC, que seguem o mesmo layout.
    """
    nao_texto = [c for c, t in df.schema.items() if t != pl.String]
    if nao_texto:
        raise ErroSchema(f"{arquivo}: esperado tudo como texto na leitura; colunas {nao_texto} não são.")

    df = df.drop([c for c in df.columns if c.startswith("Unnamed")])
    df = df.with_columns(pl.all().str.strip_chars())
    df = df.with_columns(pl.all().replace("", None))
    df = df.rename({c: RENOMEAR_CAGED[c] for c in df.columns if c in RENOMEAR_CAGED})
    presentes = set(df.columns)

    conv: dict[str, tuple[pl.Expr, str]] = {}
    for c in COLS_DECIMAL_VIRGULA:
        # '1.234,56' (milhar com ponto) vira '1.234.56' e falha de propósito.
        conv[c] = (
            pl.col(c).str.replace(",", ".", literal=True).cast(pl.Float64, strict=False),
            "número decimal com vírgula (ex.: 2018,00)",
        )
    for c in COLS_CODIGO_INTEIRO:
        conv[c] = (pl.col(c).cast(pl.Int16, strict=False), "código inteiro")
    for c in COLS_COMPETENCIA:
        v = pl.col(c).cast(pl.Int32, strict=False)
        valido = v.is_between(200001, 210012) & (v % 100).is_between(1, 12)
        conv[c] = (pl.when(valido).then(v), "competência AAAAMM válida")
    for c, largura in COLS_CODIGO_TEXTO.items():
        valido = pl.col(c).str.contains(rf"^\d{{1,{largura}}}$")
        conv[c] = (pl.when(valido).then(pl.col(c).str.zfill(largura)), f"código de até {largura} dígitos")
    conv["secao"] = (
        pl.when(pl.col("secao").str.contains(r"^[A-Z]$")).then(pl.col("secao")),
        "letra única de seção CNAE (A-Z)",
    )
    # Idade vem como '18.0'; aceita só valores inteiros.
    idade = pl.col("idade").cast(pl.Float64, strict=False)
    conv["idade"] = (pl.when(idade % 1 == 0).then(idade).cast(pl.Int16, strict=False), "idade inteira")

    conv = {c: v for c, v in conv.items() if c in presentes}
    return _converter(df, conv, arquivo)


def validar_caged(df: pl.DataFrame, arquivo: str = "CAGED MOV") -> dict:
    """Regras de consistência. Críticas geram ErroValidacao; as demais, aviso."""
    exigir_colunas(df, COLS_CRITICAS + ["uf", "tipo_movimentacao", "indicador_fora_prazo",
                                        "horas_contratuais", "idade"], arquivo)
    if df.height == 0:
        raise ErroValidacao(f"{arquivo}: nenhuma linha após a padronização.")

    # Nulos em colunas críticas.
    nulos = {c: n for c, n in zip(df.columns, df.null_count().row(0)) if n}
    criticos = {c: n for c, n in nulos.items() if c in COLS_CRITICAS}
    if criticos:
        raise ErroValidacao(f"{arquivo}: valores ausentes em colunas críticas: {criticos}")
    for c, n in nulos.items():
        avisar(f"{arquivo}: {n:,} valor(es) ausente(s) em '{c}' (mantidos como nulo).")

    saldo = pl.col("saldo_movimentacao")
    tipo = pl.col("tipo_movimentacao")
    criticas = {
        "saldo_fora_de_+1/-1": ~saldo.is_in([1, -1]),
        "uf_diferente_de_42": pl.col("uf") != 42,
        "municipio_fora_de_sc": ~pl.col("municipio_codigo").str.starts_with("42"),
        "competencia_mov_maior_que_dec": pl.col("competencia_mov") > pl.col("competencia_dec"),
        "salario_negativo": pl.col("salario") < 0,
        "horas_negativas": pl.col("horas_contratuais") < 0,
    }
    nao_criticas = {
        "admissao_com_tipo_de_desligamento": (saldo == 1) & tipo.is_in(TIPOS_DESLIGAMENTO),
        "desligamento_com_tipo_de_admissao": (saldo == -1) & tipo.is_in(TIPOS_ADMISSAO),
        "fora_prazo_inconsistente": (pl.col("indicador_fora_prazo") == 1)
        != (pl.col("competencia_mov") < pl.col("competencia_dec")),
        "idade_implausivel": ~pl.col("idade").is_between(*FAIXA_IDADE_PLAUSIVEL),
        "horas_acima_de_60": pl.col("horas_contratuais") > 60,
    }
    todas = {**criticas, **nao_criticas}
    contagens = df.select([e.fill_null(False).sum().alias(k) for k, e in todas.items()]).row(0, named=True)
    contagens["linhas_identicas (mantidas)"] = int(df.is_duplicated().sum())

    violadas = {k: contagens[k] for k in criticas if contagens[k]}
    if violadas:
        raise ErroValidacao(f"{arquivo}: regras críticas violadas (nº de linhas): {violadas}")
    for k in nao_criticas:
        if contagens[k]:
            avisar(f"{arquivo}: {contagens[k]:,} linha(s) com '{k}' (mantidas).")
    return contagens


def adicionar_colunas_derivadas(df: pl.DataFrame) -> pl.DataFrame:
    """Colunas de apoio e flags de qualidade (não removem linhas)."""
    exigir_colunas(df, ["competencia_mov", "competencia_dec", "saldo_movimentacao",
                        "salario", "idade", "origem_informacao"], "Colunas derivadas")
    if df.height == 0:
        raise ErroValidacao("Colunas derivadas: base vazia (todas as linhas foram excluídas?).")

    anos = set(df.select((pl.col("competencia_mov") // 100).unique()).to_series().to_list())
    sem_sm = sorted(anos - set(SALARIO_MINIMO))
    if sem_sm:
        raise ErroValidacao(
            f"Salário mínimo não cadastrado para o(s) ano(s) {sem_sm}. "
            "Adicione em tratamento.SALARIO_MINIMO antes de calcular as flags salariais."
        )

    janela_ini = df["competencia_dec"].min()
    janela_fim = df["competencia_dec"].max()
    ano = pl.col("competencia_mov") // 100
    sm = ano.replace_strict(SALARIO_MINIMO, return_dtype=pl.Float64)

    return df.with_columns(
        data_competencia=pl.date(ano, pl.col("competencia_mov") % 100, 1),
        movimento=pl.when(pl.col("saldo_movimentacao") > 0)
        .then(pl.lit("admissao"))
        .otherwise(pl.lit("desligamento")),
        salario_minimo_vigente=sm,
        salario_em_sm=pl.col("salario") / sm,
        # Fora da janela de 12 meses: declarações atrasadas de competências anteriores.
        flag_fora_janela=~pl.col("competencia_mov").is_between(janela_ini, janela_fim),
        flag_salario_atipico=~(pl.col("salario") / sm).is_between(*FAIXA_SALARIO_SM),
        flag_idade_ausente=pl.col("idade").is_null(),
        # Origem 3 (EmpregadoWEB) chega sem perfil: categoria/raça/horas = não identificado.
        flag_sem_perfil=pl.col("origem_informacao") == 3,
    )


def marcar_codigos_fora_dicionario(
    df: pl.DataFrame, tabelas: dict[str, pd.DataFrame]
) -> pl.DataFrame:
    """Flags para CBO e subclasse CNAE ausentes do dicionário (códigos novos)."""
    exigir_colunas(df, ["cbo2002_ocupacao", "subclasse"], "Códigos fora do dicionário")
    for aba in ("cbo2002ocupação", "subclasse"):
        if aba not in tabelas:
            raise ErroSchema(f"Dicionário de dados: aba '{aba}' ausente.")

    def validos(aba: str, largura: int) -> list[str]:
        cods = pd.to_numeric(tabelas[aba]["codigo"], errors="coerce").dropna().astype(int)
        if cods.empty:
            raise ErroSchema(f"Dicionário de dados: aba '{aba}' sem códigos numéricos.")
        return [str(c).zfill(largura) for c in cods]

    return df.with_columns(
        flag_cbo_fora_dicionario=~pl.col("cbo2002_ocupacao").is_in(validos("cbo2002ocupação", 6)),
        flag_subclasse_fora_dicionario=~pl.col("subclasse").is_in(validos("subclasse", 7)),
    )


def filtrar_exclusoes(
    mov: pl.DataFrame, exc: pl.DataFrame | None
) -> tuple[pl.DataFrame, dict]:
    """Aplica a regra MOV x EXC do Novo CAGED.

    1. Se o próprio MOV tiver ``indicador_exclusao``, mantém apenas 0 (Não).
    2. Se houver arquivo EXC, remove do MOV cada registro que aparece no EXC.
       Os microdados não têm identificador de vínculo, então o casamento é feito
       por todas as colunas do MOV. Como registros idênticos são legítimos
       (mesma empresa contratando várias pessoas com o mesmo perfil), a remoção
       é por multiconjunto: cada linha do EXC elimina no máximo uma linha do MOV.
    """
    info = {"linhas_antes": mov.height, "removidas_por_indicador": 0,
            "removidas_por_arquivo_exc": 0, "linhas_exc": None, "exc_sem_par": None}
    ignorar = {"competencia_exc", "indicador_exclusao"}

    if "indicador_exclusao" in mov.columns:
        invalidos = mov.filter(~pl.col("indicador_exclusao").is_in([0, 1]) & pl.col("indicador_exclusao").is_not_null())
        if invalidos.height:
            raise ErroValidacao(f"CAGED MOV: indicador_exclusao com valores fora de 0/1 em {invalidos.height:,} linhas.")
        antes = mov.height
        mov = mov.filter(pl.col("indicador_exclusao").fill_null(0) == 0)
        info["removidas_por_indicador"] = antes - mov.height

    if exc is not None:
        chaves = [c for c in mov.columns if c not in ignorar]
        exigir_colunas(exc, chaves, "CAGED EXC (casamento com o MOV)")
        tipos_diferentes = {c: (mov.schema[c], exc.schema[c]) for c in chaves if mov.schema[c] != exc.schema[c]}
        if tipos_diferentes:
            raise ErroSchema(f"MOV x EXC: tipos diferentes nas colunas de casamento: {tipos_diferentes}")
        if exc.height == 0:
            avisar("CAGED EXC: arquivo sem linhas; nenhuma exclusão aplicada.")

        ordem = pl.int_range(pl.len()).over(chaves).alias("_ocorrencia")
        mov_n = mov.with_columns(ordem)
        exc_n = exc.select(chaves).with_columns(ordem)

        antes = mov_n.height
        mov = mov_n.join(exc_n, on=[*chaves, "_ocorrencia"], how="anti", nulls_equal=True)
        mov = mov.drop("_ocorrencia")
        info["linhas_exc"] = exc.height
        info["removidas_por_arquivo_exc"] = antes - mov.height
        info["exc_sem_par"] = exc.height - info["removidas_por_arquivo_exc"]
        if info["exc_sem_par"]:
            avisar(
                f"MOV x EXC: {info['exc_sem_par']:,} de {exc.height:,} exclusões sem registro "
                "correspondente no MOV (podem ser de competências fora deste arquivo)."
            )

    if mov.height == 0:
        raise ErroValidacao("MOV x EXC: todas as linhas foram removidas. Verifique o arquivo EXC.")
    info["linhas_depois"] = mov.height
    return mov, info


# --------------------------------------------------------------------------- #
# Municípios (IBGE)
# --------------------------------------------------------------------------- #
RENOMEAR_MUNICIPIOS = {
    "Município [-]": "municipio_nome",
    "Código [-]": "codigo_ibge",
    "Gentílico [-]": "gentilico",
    "Prefeito [2025]": "prefeito_2025",
    "Área Territorial - km² [2025]": "area_km2_2025",
    "População no último censo - pessoas [2022]": "populacao_censo_2022",
    "Densidade demográfica - hab/km² [2022]": "densidade_hab_km2_2022",
    "População estimada - pessoas [2026]": "populacao_estimada_2026",
    "Escolarização <span>6 a 14 anos</span> - % [2022]": "escolarizacao_6a14_pct_2022",
    "IDHM <span>Índice de desenvolvimento humano municipal</span> [2010]": "idhm_2010",
    "Mortalidade infantil - óbitos por mil nascidos vivos [2025]": "mortalidade_infantil_2025",
    "Total de receitas brutas realizadas - R$ [2025]": "receitas_brutas_2025",
    "Total de despesas brutas empenhadas - R$ [2025]": "despesas_brutas_2025",
    "PIB per capita - R$ [2023]": "pib_per_capita_2023",
}
COLS_TEXTO_MUNICIPIOS = {"municipio_nome", "codigo_ibge", "gentilico", "prefeito_2025"}
COLS_INTEIRO_MUNICIPIOS = {"populacao_censo_2022", "populacao_estimada_2026"}
# Necessárias para a chave do join e para o 'saldo por 10 mil habitantes'.
COLS_OBRIGATORIAS_MUNICIPIOS = ["municipio_nome", "codigo_ibge", "populacao_estimada_2026"]
TOTAL_MUNICIPIOS_SC = 295


def tratar_municipios(df: pd.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Limpa o CSV do IBGE e cria a chave ``municipio_codigo`` (6 dígitos, igual ao CAGED)."""
    arquivo = "Municípios SC (IBGE)"
    info = {"linhas_brutas": len(df)}

    ausentes = [orig for orig in RENOMEAR_MUNICIPIOS if orig not in df.columns]
    df = df.loc[:, [c for c in df.columns if c in RENOMEAR_MUNICIPIOS]]
    df = df.rename(columns=RENOMEAR_MUNICIPIOS)
    exigir_colunas(df, COLS_OBRIGATORIAS_MUNICIPIOS, arquivo)
    if ausentes:
        avisar(f"{arquivo}: colunas opcionais ausentes (ignoradas): {ausentes}")
    df = df.apply(lambda s: s.str.strip())

    # Separa linhas de município do rodapé HTML de notas/fontes exportado pelo IBGE.
    eh_municipio = df["codigo_ibge"].str.fullmatch(r"42\d{5}", na=False)
    eh_rodape = df["municipio_nome"].str.startswith("<", na=False) | (df["municipio_nome"] == "")
    estranhas = df.loc[~eh_municipio & ~eh_rodape, ["municipio_nome", "codigo_ibge"]]
    if not estranhas.empty:
        raise ErroValidacao(
            f"{arquivo}: {len(estranhas)} linha(s) sem código IBGE de SC válido (42xxxxx) "
            f"que não são rodapé: {estranhas.head(5).to_dict(orient='records')}"
        )
    info["linhas_removidas_rodape"] = int((~eh_municipio).sum())
    df = df.loc[eh_municipio].copy()

    # '-' é o marcador do IBGE para dado indisponível.
    info["valores_indisponiveis"] = {c: int(n) for c, n in (df == "-").sum().items() if n > 0}
    df = df.replace({"-": None, "": None})

    for c in df.columns:
        if c in COLS_TEXTO_MUNICIPIOS:
            continue
        convertido = pd.to_numeric(df[c], errors="coerce")
        falhou = df[c].notna() & convertido.isna()
        if falhou.any():
            raise ErroConversao(arquivo, c, int(falhou.sum()), df.loc[falhou, c].unique()[:5].tolist(),
                                "número com ponto decimal")
        if c in COLS_INTEIRO_MUNICIPIOS:
            fracionario = convertido.notna() & (convertido % 1 != 0)
            if fracionario.any():
                raise ErroConversao(arquivo, c, int(fracionario.sum()),
                                    df.loc[fracionario, c].unique()[:5].tolist(), "inteiro")
            convertido = convertido.astype("Int64")
        df[c] = convertido

    pop = df["populacao_estimada_2026"]
    pop_ruim = (pop.isna() | (pop <= 0).fillna(False)).astype(bool)
    if pop_ruim.any():
        ruins = df.loc[pop_ruim, "municipio_nome"].tolist()
        raise ErroValidacao(f"{arquivo}: população estimada ausente ou <= 0 em: {ruins[:10]}")

    df.insert(0, "municipio_codigo", df["codigo_ibge"].str[:6])
    duplicados = df.loc[df["municipio_codigo"].duplicated(keep=False), ["municipio_codigo", "municipio_nome"]]
    if not duplicados.empty:
        raise ErroValidacao(
            f"{arquivo}: municipio_codigo repetido (duplicaria linhas no join): "
            f"{duplicados.to_dict(orient='records')}"
        )
    if len(df) != TOTAL_MUNICIPIOS_SC:
        avisar(f"{arquivo}: {len(df)} municípios; SC tem {TOTAL_MUNICIPIOS_SC}.")

    info["linhas_finais"] = len(df)
    info["codigos_duplicados"] = 0
    return pl.from_pandas(df), info
