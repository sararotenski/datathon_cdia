"""Erros e avisos do pipeline.

Erros (exceções) interrompem a execução: indicam dado que tornaria o
resultado errado. Avisos são registrados e o pipeline continua.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("pipeline")

# Avisos emitidos durante a execução (vão para o relatório da etapa).
AVISOS: list[str] = []


class ErroPipeline(Exception):
    """Base de todos os erros esperados do pipeline."""


class ErroArquivo(ErroPipeline):
    """Arquivo ausente, vazio, ilegível ou impossível de gravar."""


class ErroSchema(ErroPipeline):
    """Colunas ou abas diferentes do esperado."""


class ErroConversao(ErroPipeline):
    """Valores que não puderam ser convertidos para o tipo esperado."""

    def __init__(self, arquivo: str, coluna: str, n_linhas: int, exemplos: list, esperado: str):
        self.coluna = coluna
        self.n_linhas = n_linhas
        self.exemplos = exemplos
        super().__init__(
            f"[{arquivo}] coluna '{coluna}': {n_linhas:,} valor(es) não convertido(s) "
            f"para {esperado}. Exemplos: {exemplos}"
        )


class ErroValidacao(ErroPipeline):
    """Regra de negócio crítica violada (ex.: saldo diferente de +1/-1)."""


def avisar(mensagem: str) -> None:
    AVISOS.append(mensagem)
    logger.warning(mensagem)
