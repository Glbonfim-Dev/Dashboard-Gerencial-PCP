"""Detecta alteracoes no Excel compartilhado e aciona a publicacao do dashboard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from config import PROJECT_DIR
from logger import configurar_logger


ESTADO_PADRAO = PROJECT_DIR / "automation" / "estado_monitor.json"
Publicador = Callable[[Path], int]


def assinatura_arquivo(caminho: Path) -> dict[str, int]:
    """Retorna uma assinatura barata e suficiente para detectar um novo salvamento."""

    atributos = caminho.stat()
    return {"tamanho": atributos.st_size, "modificado_ns": atributos.st_mtime_ns}


def ler_estado(caminho: Path) -> dict[str, int] | None:
    """Le o ultimo salvamento publicado; estado invalido causa novo processamento."""

    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados.get("tamanho"), int) and isinstance(
            dados.get("modificado_ns"), int
        ):
            return {
                "tamanho": dados["tamanho"],
                "modificado_ns": dados["modificado_ns"],
            }
    except (FileNotFoundError, OSError, json.JSONDecodeError, AttributeError):
        pass
    return None


def salvar_estado(caminho: Path, assinatura: dict[str, int]) -> None:
    """Grava o estado de forma atomica para nao perder uma alteracao apos falhas."""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(assinatura, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)


def executar_publicacao(caminho_excel: Path) -> int:
    """Executa o publicador com o mesmo Python usado pelo monitor."""

    resultado = subprocess.run(
        [sys.executable, str(PROJECT_DIR / "publicar_dashboard.py"), str(caminho_excel)],
        cwd=PROJECT_DIR,
        check=False,
    )
    return resultado.returncode


def monitorar_uma_vez(
    caminho_excel: Path,
    caminho_estado: Path = ESTADO_PADRAO,
    *,
    forcar: bool = False,
    espera_estabilidade: float = 3,
    publicador: Publicador = executar_publicacao,
) -> int:
    """Publica somente quando o arquivo mudou e permaneceu estavel por alguns segundos."""

    logger = configurar_logger()
    try:
        assinatura_inicial = assinatura_arquivo(caminho_excel)
    except OSError as erro:
        logger.error("Monitor nao conseguiu consultar o Excel compartilhado: %s", erro)
        return 1

    if not forcar and assinatura_inicial == ler_estado(caminho_estado):
        return 0

    logger.info("Monitor detectou alteracao no Excel compartilhado")
    if espera_estabilidade > 0:
        time.sleep(espera_estabilidade)

    try:
        assinatura_estavel = assinatura_arquivo(caminho_excel)
    except OSError as erro:
        logger.warning("Excel ficou indisponivel durante a verificacao: %s", erro)
        return 1

    if assinatura_estavel != assinatura_inicial:
        logger.info("Excel ainda esta sendo salvo; processamento adiado")
        return 0

    codigo = publicador(caminho_excel)
    if codigo == 0:
        salvar_estado(caminho_estado, assinatura_estavel)
        logger.info("Monitor registrou o salvamento como publicado")
    else:
        logger.warning(
            "Publicacao retornou codigo %d; o monitor tentara novamente", codigo
        )
    return codigo


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitora um Excel compartilhado e atualiza o dashboard quando ele muda."
    )
    parser.add_argument("excel", help="Caminho UNC completo do arquivo .xlsm/.xlsx")
    parser.add_argument("--forcar", action="store_true", help="Publica mesmo sem alteracao")
    parser.add_argument(
        "--estado",
        type=Path,
        default=ESTADO_PADRAO,
        help="Arquivo que armazena a assinatura do ultimo salvamento publicado",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argumentos = criar_parser().parse_args(argv)
    caminho_excel = Path(argumentos.excel)
    if caminho_excel.suffix.lower() not in {".xlsm", ".xlsx"}:
        criar_parser().error("o arquivo monitorado deve ser .xlsm ou .xlsx")
    return monitorar_uma_vez(
        caminho_excel,
        argumentos.estado,
        forcar=argumentos.forcar,
    )


if __name__ == "__main__":
    raise SystemExit(main())
