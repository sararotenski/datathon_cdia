"""Pipeline do Datathon - Etapa 1: Ingestão e Validação.

Uso (a partir da raiz do projeto):
    .venv/bin/python src/pipeline.py

Saídas em data/processados/:
    caged_mov_tratado.parquet   movimentações tipadas, com exclusões aplicadas e flags
    municipios_sc.parquet       municípios de SC com chave municipio_codigo (6 dígitos)
    relatorio_etapa1.json       números e avisos de cada passo (para o pitch/metodologia)

Códigos de saída: 0 = sucesso; 1 = erro nos dados/arquivos (mensagem explica o
motivo); 2 = erro inesperado (bug, traceback completo).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import polars as pl

import erros
import ingestao as ing
import tratamento as trt
from erros import ErroArquivo, ErroPipeline, ErroValidacao

logger = logging.getLogger("pipeline")


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n{texto}\n{'=' * 70}")


def gravar_atomico(destino: Path, escrever) -> None:
    """Grava em arquivo temporário e renomeia: nunca deixa saída pela metade."""
    tmp = destino.with_name(destino.name + ".tmp")
    try:
        escrever(tmp)
        tmp.replace(destino)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        raise ErroArquivo(f"Falha ao gravar '{destino}' (permissão ou espaço em disco?). {e}") from e
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def etapa_1() -> dict:
    erros.AVISOS.clear()
    rel: dict = {}

    # ------------------------------------------------------------------ 1
    titulo("1. Dicionário de dados")
    layout = ing.carregar_layout()
    tabelas = ing.carregar_tabelas_codigos()
    print(f"Layout: {len(layout)} variáveis | tabelas de códigos: {len(tabelas)}")

    # ------------------------------------------------------------------ 2
    titulo("2. Carga do CAGED MOV e verificação de schema")
    mov_bruto = ing.carregar_caged_mov()
    schema = ing.verificar_schema_caged(mov_bruto, layout, tipo="MOV")
    rel["schema_caged"] = schema
    print(f"Linhas: {schema['linhas']:,} | colunas: {schema['colunas']}")
    print(f"Colunas de índice do pandas (removidas): {schema['colunas_indice_removiveis']}")
    print(f"Colunas exclusivas do EXC presentes no MOV: {schema['colunas_exc_presentes'] or 'nenhuma'}")
    print("Schema compatível com o layout MOV.")

    # ------------------------------------------------------------------ 3
    titulo("3. Padronização de tipos")
    mov = trt.padronizar_caged(mov_bruto, arquivo=ing.ARQ_CAGED_MOV.name)
    del mov_bruto
    print(mov.schema)

    # ------------------------------------------------------------------ 4
    titulo("4. Validação de códigos contra o dicionário")
    validacao = ing.verificar_codigos(mov, tabelas, trt.RENOMEAR_CAGED)
    rel["codigos_fora_dicionario"] = validacao.to_dict(orient="records")
    print(validacao.to_string(index=False))

    # ------------------------------------------------------------------ 5
    titulo("5. Consistência interna")
    checks = trt.validar_caged(mov)
    rel["consistencia"] = checks
    for k, v in checks.items():
        print(f"  {k:<40} {v:>10,}")
    print("  Linhas idênticas são esperadas: os microdados não têm ID de pessoa/empresa.")

    # ------------------------------------------------------------------ 6
    titulo("6. Filtragem das exclusões (MOV x EXC)")
    exc_path = ing.localizar_caged_exc()
    exc = ing.carregar_caged_exc(exc_path)
    if exc is not None:
        rel["schema_exc"] = ing.verificar_schema_caged(exc, layout, tipo="EXC")
        exc = trt.padronizar_caged(exc, arquivo=exc_path.name)
        print(f"Arquivo EXC encontrado: {exc_path.name} ({exc.height:,} linhas)")
    elif "indicador_exclusao" not in mov.columns:
        erros.avisar(
            "Exclusões não aplicadas: não há arquivo EXC em data/brutos e o MOV não tem "
            "indicadordeexclusão. Decisão da equipe: seguir sem os arquivos CAGEDEXC do MTE "
            "(efeito medido em 10/11/2026: +90 no saldo de 12 meses de SC, +16 na seção C)."
        )
    mov, info_exc = trt.filtrar_exclusoes(mov, exc)
    info_exc["arquivo_exc"] = exc_path.name if exc_path else None
    rel["exclusoes"] = info_exc
    print(info_exc)

    # ------------------------------------------------------------------ 7
    titulo("7. Colunas derivadas e flags de qualidade")
    mov = trt.adicionar_colunas_derivadas(mov)
    mov = trt.marcar_codigos_fora_dicionario(mov, tabelas)
    flags = {c: int(mov[c].sum()) for c in mov.columns if c.startswith("flag_")}
    rel["flags"] = flags
    for k, v in flags.items():
        print(f"  {k:<36} {v:>10,} ({v / mov.height:.2%})")
    print(mov.group_by("movimento").len().sort("movimento"))
    rel["saldo_total"] = int(mov["saldo_movimentacao"].sum())
    print(f"Saldo total (todas as linhas): {rel['saldo_total']:,}")
    saldo_janela = int(mov.filter(~pl.col("flag_fora_janela"))["saldo_movimentacao"].sum())
    rel["saldo_janela_12m"] = saldo_janela
    print(f"Saldo dentro da janela {mov['competencia_dec'].min()}–{mov['competencia_dec'].max()}: "
          f"{saldo_janela:,}")

    # ------------------------------------------------------------------ 8
    titulo("8. Municípios (IBGE) e cobertura da chave municipio_codigo")
    mun, info_mun = trt.tratar_municipios(ing.carregar_municipios())
    caged_mun = set(mov["municipio_codigo"].unique())
    ibge_mun = set(mun["municipio_codigo"])
    info_mun["caged_sem_ibge"] = sorted(caged_mun - ibge_mun)
    info_mun["ibge_sem_caged"] = sorted(ibge_mun - caged_mun)
    rel["municipios"] = info_mun
    if info_mun["caged_sem_ibge"]:
        linhas = mov.filter(pl.col("municipio_codigo").is_in(info_mun["caged_sem_ibge"])).height
        raise ErroValidacao(
            f"{len(info_mun['caged_sem_ibge'])} município(s) do CAGED sem correspondência no IBGE "
            f"({linhas:,} linhas seriam perdidas no join): {info_mun['caged_sem_ibge'][:10]}"
        )
    if info_mun["ibge_sem_caged"]:
        erros.avisar(f"Municípios sem nenhuma movimentação no CAGED: {info_mun['ibge_sem_caged']}")
    print(info_mun)
    print(mun.schema)

    # ------------------------------------------------------------------ 9
    titulo("9. Exportação")
    rel["avisos"] = list(erros.AVISOS)
    try:
        ing.DIR_PROCESSADOS.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ErroArquivo(f"Não foi possível criar '{ing.DIR_PROCESSADOS}'. {e}") from e

    gravar_atomico(ing.DIR_PROCESSADOS / "caged_mov_tratado.parquet", mov.write_parquet)
    gravar_atomico(ing.DIR_PROCESSADOS / "municipios_sc.parquet", mun.write_parquet)

    def escrever_json(caminho: Path) -> None:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(rel, f, ensure_ascii=False, indent=2, default=str)

    gravar_atomico(ing.DIR_PROCESSADOS / "relatorio_etapa1.json", escrever_json)
    print(f"CAGED tratado: {mov.height:,} linhas x {mov.width} colunas")
    print(f"Municípios:    {mun.height} linhas x {mun.width} colunas")
    print(f"Arquivos em {ing.DIR_PROCESSADOS}")

    titulo(f"Avisos ({len(rel['avisos'])})")
    for a in rel["avisos"]:
        print(f"  - {a}")
    return rel


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="AVISO: %(message)s")
    try:
        etapa_1()
    except ErroPipeline as e:
        print(f"\nERRO ({type(e).__name__}): {e}", file=sys.stderr)
        print("Corrija o problema e rode novamente; as saídas em data/processados "
              "não refletem esta execução.", file=sys.stderr)
        return 1
    except Exception:
        logger.exception("Erro inesperado (provável bug no código):")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
