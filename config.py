"""Configuracao central da automacao.

Altere somente este arquivo quando colunas ou abas da planilha mudarem.
As colunas opcionais podem permanecer como ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# Caminhos sempre relativos à pasta onde o projeto está instalado.
PROJECT_DIR = Path(__file__).resolve().parent
JSON_OUTPUT_PATH = PROJECT_DIR / "dados.json"
LOCK_PATH = PROJECT_DIR / "dashboard.lock"

# Política de espera aplicada logo após o salvamento do Excel.
EXCEL_MAX_TENTATIVAS = 10
EXCEL_INTERVALO_SEGUNDOS = 2
VENCIMENTO_PROXIMO_DIAS = 30


@dataclass(frozen=True)
class AcoesConfig:
    """Mapeamento das colunas usadas na aba de ações."""

    aba: str = "AÇÕES DE MELHORIA"
    linha_inicial: int = 8
    coluna_acao: str = "F"
    coluna_responsavel: str = "G"
    coluna_prazo: str = "H"
    coluna_status: str = "J"
    coluna_observacao: str | None = None
    coluna_data_conclusao: str | None = None


@dataclass(frozen=True)
class FaturamentoConfig:
    """Mapeamento da aba de faturamento e metas mensais oficiais."""

    aba: str = "FATURAMENTO MOLDES 2026"
    linha_inicial: int = 15
    linha_final: int = 26
    coluna_mes: str = "D"
    coluna_realizado: str = "H"
    coluna_meta: str | None = None
    ano: int = 2026
    # Meta mensal oficial. Caso as metas passem a existir no Excel, configure
    # coluna_meta para que os valores sejam lidos diretamente da planilha.
    metas_mensais: dict[str, float] = field(
        default_factory=lambda: {
            "JANEIRO": 1_000_000.0,
            "FEVEREIRO": 1_000_000.0,
            "MARÇO": 1_000_000.0,
            "ABRIL": 1_000_000.0,
            "MAIO": 1_000_000.0,
            "JUNHO": 1_000_000.0,
            "JULHO": 1_000_000.0,
            "AGOSTO": 1_000_000.0,
            "SETEMBRO": 1_000_000.0,
            "OUTUBRO": 1_000_000.0,
            "NOVEMBRO": 1_000_000.0,
            "DEZEMBRO": 1_000_000.0,
        }
    )


# Instâncias compartilhadas pelos módulos de leitura e cálculo.
ACOES_CONFIG = AcoesConfig()
FATURAMENTO_CONFIG = FaturamentoConfig()


@dataclass(frozen=True)
class QualidadeConfig:
    """A leitura da qualidade identifica os blocos pelos cabeçalhos, não por células."""

    aba: str = "Qualidade KPI 2026"
    ano: int = 2026


QUALIDADE_CONFIG = QualidadeConfig()
