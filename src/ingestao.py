"""Etapa 1a - Ingestão: carga dos arquivos brutos e verificação de schema.

Tudo é lido como texto (``infer_schema=False``) para que nenhuma conversão
implícita esconda problemas. A tipagem acontece em ``tratamento.py``.

Qualquer problema de leitura vira ``ErroArquivo`` ou ``ErroSchema`` com o nome
do arquivo e a ação esperada, em vez do traceback cru da biblioteca.
"""

from __future__ import annotations

import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd
import polars as pl

from erros import ErroArquivo, ErroSchema, avisar

RAIZ = Path(__file__).resolve().parents[1]
DIR_BRUTOS = RAIZ / "data" / "brutos"
DIR_PROCESSADOS = RAIZ / "data" / "processados"

ARQ_CAGED_MOV = DIR_BRUTOS / "Novo_Caged_MOV_Limpo.csv"
ARQ_MUNICIPIOS = DIR_BRUTOS / "Municipios_SC_limpo.csv"
ARQ_DICIONARIO = DIR_BRUTOS / "Dicionario_de_dados.xlsx"

# Colunas que o layout oficial do Novo CAGED só traz no arquivo de exclusões (EXC).
COLUNAS_SO_EXC = {"competênciaexc", "indicadordeexclusão"}

# Colunas de índice que o pandas gravou no CSV ao exportar (lixo de exportação).
COLUNAS_INDICE_PANDAS = {"Unnamed: 0", "Unnamed: 0.1"}

# Abas do dicionário usadas pelo tratamento (sem elas não há como validar códigos).
ABAS_OBRIGATORIAS = {"Layout", "cbo2002ocupação", "subclasse", "município", "seção"}


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #
def checar_arquivo(caminho: Path, descricao: str) -> Path:
    """Garante que o arquivo existe, é um arquivo e não está vazio."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroArquivo(
            f"{descricao} não encontrado em '{caminho}'. "
            f"Coloque o arquivo em {DIR_BRUTOS} com esse nome."
        )
    if not caminho.is_file():
        raise ErroArquivo(f"{descricao}: '{caminho}' não é um arquivo.")
    if caminho.stat().st_size == 0:
        raise ErroArquivo(f"{descricao}: '{caminho.name}' está vazio (0 bytes).")
    return caminho


def _ler_csv_polars(caminho: Path, descricao: str, separador: str) -> pl.DataFrame:
    checar_arquivo(caminho, descricao)
    try:
        df = pl.read_csv(caminho, separator=separador, infer_schema=False, encoding="utf8")
    except pl.exceptions.NoDataError as e:
        raise ErroArquivo(f"{descricao}: '{caminho.name}' não tem dados.") from e
    except pl.exceptions.DuplicateError as e:
        raise ErroSchema(f"{descricao}: '{caminho.name}' tem colunas com nome repetido. {e}") from e
    except pl.exceptions.ComputeError as e:
        # Polars reporta UTF-8 inválido e linhas com nº de campos errado como ComputeError.
        raise ErroArquivo(
            f"{descricao}: falha ao ler '{caminho.name}'. Verifique se está em UTF-8 e "
            f"separado por '{separador}'. Detalhe: {str(e).splitlines()[0]}"
        ) from e
    except pl.exceptions.PolarsError as e:
        raise ErroArquivo(f"{descricao}: erro do polars ao ler '{caminho.name}'. {e}") from e
    except OSError as e:
        raise ErroArquivo(f"{descricao}: sem permissão ou erro de disco em '{caminho}'. {e}") from e

    # O polars valida UTF-8 nos dados, mas troca bytes inválidos do cabeçalho por '�'.
    if any("\ufffd" in c for c in df.columns):
        raise ErroArquivo(
            f"{descricao}: cabeçalho de '{caminho.name}' não está em UTF-8 "
            f"(provavelmente latin-1). Salve novamente como UTF-8."
        )
    if df.width == 1:
        raise ErroSchema(
            f"{descricao}: '{caminho.name}' foi lido com uma única coluna. "
            f"O separador esperado é '{separador}'; o arquivo provavelmente usa outro."
        )
    if df.height == 0:
        raise ErroArquivo(f"{descricao}: '{caminho.name}' tem cabeçalho mas nenhuma linha.")
    return df


# --------------------------------------------------------------------------- #
# Dicionário de dados
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _ler_dicionario(caminho: Path) -> dict[str, pd.DataFrame]:
    checar_arquivo(caminho, "Dicionário de dados")
    try:
        abas = pd.read_excel(caminho, sheet_name=None, header=None, dtype=str)
    except (zipfile.BadZipFile, ValueError) as e:
        raise ErroArquivo(
            f"Dicionário de dados: '{caminho.name}' não é um .xlsx válido ou está corrompido. {e}"
        ) from e
    except OSError as e:
        raise ErroArquivo(f"Dicionário de dados: erro ao abrir '{caminho}'. {e}") from e

    abas = {nome.strip(): tab for nome, tab in abas.items()}
    faltando = ABAS_OBRIGATORIAS - set(abas)
    if faltando:
        raise ErroSchema(f"Dicionário de dados: abas obrigatórias ausentes: {sorted(faltando)}")
    return abas


def carregar_layout(caminho: Path = ARQ_DICIONARIO) -> pd.DataFrame:
    """Aba 'Layout' do dicionário: variável, descrição e formato."""
    bruto = _ler_dicionario(Path(caminho))["Layout"]
    # Localiza o cabeçalho pela palavra 'Variável' em vez de supor a linha.
    col0 = bruto.iloc[:, 0].astype(str).str.strip()
    linhas_cab = col0.index[col0 == "Variável"]
    if len(linhas_cab) == 0 or bruto.shape[1] < 3:
        raise ErroSchema("Dicionário de dados: aba 'Layout' sem cabeçalho 'Variável | Descrição | Código'.")

    layout = bruto.iloc[linhas_cab[0] + 1:, :3].copy()
    layout.columns = ["variavel", "descricao", "formato"]
    layout = layout.dropna(subset=["variavel"])
    layout["variavel"] = layout["variavel"].str.strip()
    if layout.empty:
        raise ErroSchema("Dicionário de dados: aba 'Layout' não lista nenhuma variável.")
    if layout["variavel"].duplicated().any():
        dup = layout.loc[layout["variavel"].duplicated(), "variavel"].tolist()
        raise ErroSchema(f"Dicionário de dados: variáveis repetidas no Layout: {dup}")
    return layout.reset_index(drop=True)


def carregar_tabelas_codigos(caminho: Path = ARQ_DICIONARIO) -> dict[str, pd.DataFrame]:
    """Demais abas do dicionário: uma tabela código -> descrição por variável."""
    tabelas = {}
    for nome, bruto in _ler_dicionario(Path(caminho)).items():
        if nome == "Layout":
            continue
        if bruto.shape[1] < 2 or str(bruto.iat[0, 0]).strip() != "Código":
            avisar(f"Dicionário: aba '{nome}' ignorada (sem cabeçalho 'Código | Descrição').")
            continue
        tab = bruto.iloc[1:, :2].copy()
        tab.columns = ["codigo", "descricao"]
        tab["codigo"] = tab["codigo"].str.strip()
        tab["descricao"] = tab["descricao"].str.strip()
        tab = tab.dropna(subset=["codigo"])
        repetidos = tab["codigo"].duplicated().sum()
        if repetidos:
            avisar(f"Dicionário: aba '{nome}' tem {repetidos} código(s) repetido(s); mantida a 1ª descrição.")
            tab = tab.drop_duplicates(subset="codigo")
        tabelas[nome] = tab.reset_index(drop=True)

    faltando = (ABAS_OBRIGATORIAS - {"Layout"}) - set(tabelas)
    if faltando:
        raise ErroSchema(f"Dicionário de dados: abas de códigos ilegíveis: {sorted(faltando)}")
    return tabelas


# --------------------------------------------------------------------------- #
# Arquivos de dados
# --------------------------------------------------------------------------- #
def carregar_caged_mov(caminho: Path = ARQ_CAGED_MOV) -> pl.DataFrame:
    """CSV do Novo CAGED (separador ';', decimal ',', UTF-8). Tudo como texto."""
    return _ler_csv_polars(Path(caminho), "CAGED MOV", ";")


def localizar_caged_exc(diretorio: Path = DIR_BRUTOS) -> Path | None:
    """Procura um arquivo de exclusões (CAGEDEXC) em data/brutos.

    Retorna None se não houver. Mais de um candidato é erro: escolher um
    arbitrariamente poderia aplicar as exclusões erradas.
    """
    if not diretorio.is_dir():
        raise ErroArquivo(f"Pasta de dados brutos não encontrada: '{diretorio}'.")
    candidatos = sorted(
        p for p in diretorio.iterdir()
        if p.is_file() and p.suffix.lower() in {".csv", ".txt"} and "exc" in p.stem.lower()
    )
    if len(candidatos) > 1:
        raise ErroArquivo(
            f"Mais de um arquivo de exclusões em {diretorio}: {[p.name for p in candidatos]}. "
            "Deixe apenas um (ou junte-os em um único arquivo)."
        )
    return candidatos[0] if candidatos else None


def carregar_caged_exc(caminho: Path | None) -> pl.DataFrame | None:
    """Carrega o arquivo de exclusões. Retorna None se ``caminho`` for None."""
    if caminho is None:
        return None
    return _ler_csv_polars(Path(caminho), "CAGED EXC", ";")


def carregar_municipios(caminho: Path = ARQ_MUNICIPIOS) -> pd.DataFrame:
    """CSV do IBGE (separador ','). Tudo como texto; a limpeza fica no tratamento."""
    caminho = checar_arquivo(Path(caminho), "Municípios SC (IBGE)")
    try:
        df = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ErroArquivo(
            f"Municípios SC (IBGE): '{caminho.name}' não está em UTF-8. "
            f"Salve novamente como CSV UTF-8. Detalhe: {e}"
        ) from e
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise ErroArquivo(f"Municípios SC (IBGE): falha ao ler '{caminho.name}'. {e}") from e
    except OSError as e:
        raise ErroArquivo(f"Municípios SC (IBGE): erro ao abrir '{caminho}'. {e}") from e

    if df.shape[1] == 1:
        raise ErroSchema(
            f"Municípios SC (IBGE): '{caminho.name}' foi lido com uma única coluna; "
            "o separador esperado é ','."
        )
    return df


# --------------------------------------------------------------------------- #
# Verificação de schema
# --------------------------------------------------------------------------- #
def verificar_schema_caged(df: pl.DataFrame, layout: pd.DataFrame, tipo: str = "MOV") -> dict:
    """Compara as colunas do arquivo com o layout do dicionário e falha se divergirem.

    MOV: todas as colunas do layout, exceto as exclusivas do EXC.
    EXC: todas as colunas do layout, inclusive competênciaexc e indicadordeexclusão.
    Em ambos, só são toleradas como extras as colunas de índice do pandas.
    """
    if tipo not in {"MOV", "EXC"}:
        raise ValueError(f"tipo deve ser 'MOV' ou 'EXC', não {tipo!r}")

    layout_cols = set(layout["variavel"])
    esperadas = layout_cols - COLUNAS_SO_EXC if tipo == "MOV" else layout_cols
    presentes = set(df.columns)
    faltando = sorted(esperadas - presentes)
    extras = sorted(presentes - layout_cols - COLUNAS_INDICE_PANDAS)

    resultado = {
        "tipo": tipo,
        "linhas": df.height,
        "colunas": df.width,
        "faltando_no_arquivo": faltando,
        "colunas_indice_removiveis": sorted(presentes & COLUNAS_INDICE_PANDAS),
        "extras_desconhecidas": extras,
        "colunas_exc_presentes": sorted(presentes & COLUNAS_SO_EXC),
    }
    if faltando or extras:
        raise ErroSchema(
            f"CAGED {tipo}: schema diferente do layout do dicionário. "
            f"Faltando: {faltando} | Extras desconhecidas: {extras}"
        )
    return resultado


def verificar_codigos(
    df: pl.DataFrame,
    tabelas: dict[str, pd.DataFrame],
    mapa_colunas: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Para cada coluna categórica com tabela no dicionário, conta códigos ausentes dela.

    ``mapa_colunas`` traduz o nome da aba do dicionário para o nome da coluna em
    ``df`` (útil depois da renomeação para snake_case).

    Códigos numéricos são comparados pelo valor inteiro, para não depender de
    zeros à esquerda (ex.: CBO '010105' no CSV x '10105' no dicionário).
    Códigos alfabéticos (ex.: seção CNAE 'C') são comparados como texto.
    """
    mapa_colunas = mapa_colunas or {}
    linhas = []
    for aba, tab in tabelas.items():
        col = mapa_colunas.get(aba, aba)
        if col not in df.columns:
            continue
        numericos = pd.to_numeric(tab["codigo"], errors="coerce")
        if numericos.notna().all():
            validos = set(numericos.astype(int))
            cod = pl.col(col).cast(pl.Int64, strict=False)
        else:
            validos = set(tab["codigo"])
            cod = pl.col(col).cast(pl.String)
        vc = df.select(cod.alias("cod")).group_by("cod").len()
        invalidos = vc.filter(~pl.col("cod").is_in(list(validos)) | pl.col("cod").is_null())
        linhas.append({
            "coluna": col,
            "codigos_distintos": vc.height,
            "codigos_fora_dicionario": invalidos.height,
            "linhas_afetadas": int(invalidos["len"].sum()),
            "exemplos": invalidos.sort("len", descending=True)["cod"].head(5).to_list(),
        })
    return pd.DataFrame(linhas)
