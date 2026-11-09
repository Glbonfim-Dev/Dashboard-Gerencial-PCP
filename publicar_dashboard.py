"""Gera e publica os dados do dashboard a partir de um arquivo Excel."""

from __future__ import annotations

import argparse
import json
import msvcrt
import os
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

from dotenv import load_dotenv

from config import JSON_OUTPUT_PATH, LOCK_PATH, PROJECT_DIR
from excel_reader import (
    ExcelReaderError,
    aguardar_arquivo_disponivel,
    calcular_indicadores,
    carregar_dados_excel,
)
from github_client import GitHubClient, GitHubConfig
from logger import configurar_logger


class ExecucaoEmAndamento(RuntimeError):
    """Outra instancia ja possui o lock da automacao."""


class ExecucaoLock:
    """Lock exclusivo no Windows, liberado automaticamente se o processo morrer."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.arquivo: BinaryIO | None = None

    def __enter__(self) -> "ExecucaoLock":
        """Adquire um byte exclusivo do arquivo de lock no Windows."""

        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        arquivo = self.caminho.open("a+b")
        try:
            arquivo.seek(0, os.SEEK_END)
            if arquivo.tell() == 0:
                arquivo.write(b"0")
                arquivo.flush()
            arquivo.seek(0)
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            arquivo.seek(0)
            arquivo.truncate()
            arquivo.write(f"pid={os.getpid()}\n".encode("ascii"))
            arquivo.flush()
            self.arquivo = arquivo
            return self
        except OSError as erro:
            arquivo.close()
            raise ExecucaoEmAndamento("outra execucao ja esta ativa") from erro

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Libera o byte, fecha o arquivo e remove o lock ao terminar."""

        if self.arquivo is None:
            return
        try:
            self.arquivo.seek(0)
            msvcrt.locking(self.arquivo.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.arquivo.close()
            self.arquivo = None
            try:
                self.caminho.unlink(missing_ok=True)
            except OSError:
                pass


def criar_parser() -> argparse.ArgumentParser:
    """Define os argumentos aceitos pela linha de comando e pelo VBA."""

    parser = argparse.ArgumentParser(
        description="Le o Excel, gera dados.json e o publica no GitHub."
    )
    parser.add_argument("excel", nargs="?", help="Caminho completo do arquivo .xlsm/.xlsx")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Gera o JSON localmente sem publicar no GitHub.",
    )
    return parser


def validar_caminho(valor: str | None) -> Path:
    """Confirma presença, extensão permitida e existência do Excel."""

    if not valor:
        raise ValueError("nenhum caminho de Excel foi informado")
    caminho = Path(valor).expanduser()
    if caminho.suffix.lower() not in {".xlsm", ".xlsx"}:
        raise ValueError("o arquivo deve possuir extensao .xlsm ou .xlsx")
    try:
        existe = caminho.is_file()
    except OSError as erro:
        raise ValueError(f"nao foi possivel consultar o arquivo: {erro}") from erro
    if not existe:
        raise ValueError(f"arquivo nao encontrado: {caminho}")
    return caminho


def escrever_json_atomico(dados: dict[str, object], destino: Path) -> bytes:
    """Grava primeiro em arquivo temporário para nunca deixar JSON incompleto."""

    conteudo = json.dumps(
        dados,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(destino)
    return conteudo


def config_github_do_ambiente() -> GitHubConfig:
    """Lê as credenciais do ambiente sem expor seus valores em logs."""

    return GitHubConfig(
        token=os.getenv("GITHUB_TOKEN", "").strip(),
        owner=os.getenv("GITHUB_OWNER", "").strip(),
        repo=os.getenv("GITHUB_REPO", "").strip(),
        branch=os.getenv("GITHUB_BRANCH", "main").strip() or "main",
        json_path=os.getenv("GITHUB_JSON_PATH", "dados.json").strip() or "dados.json",
    )


def main(argv: list[str] | None = None) -> int:
    """Executa validação, leitura, cálculo, JSON e publicação em sequência."""

    logger = configurar_logger()
    argumentos = criar_parser().parse_args(argv)
    logger.info("Inicio da execucao")
    logger.info("Arquivo recebido: %s", argumentos.excel or "NAO_INFORMADO")

    try:
        caminho_excel = validar_caminho(argumentos.excel)
    except ValueError as erro:
        logger.error("Entrada invalida: %s", erro)
        return 2

    try:
        # O contexto garante a remoção do lock mesmo quando ocorre uma exceção.
        with ExecucaoLock(LOCK_PATH):
            logger.info("Lock de execucao adquirido")
            aguardar_arquivo_disponivel(caminho_excel, logger)
            acoes, faturamento = carregar_dados_excel(caminho_excel, logger)
            dados = calcular_indicadores(acoes, faturamento, caminho_excel.name)
            logger.info(
                "Indicadores calculados: %d acoes, %d atrasadas",
                dados["acoes"]["total"],
                dados["acoes"]["atrasadas"],
            )

            conteudo_json = escrever_json_atomico(dados, JSON_OUTPUT_PATH)
            logger.info("JSON criado em %s", JSON_OUTPUT_PATH)

            load_dotenv(PROJECT_DIR / ".env")
            github_config = config_github_do_ambiente()
            if argumentos.no_upload:
                logger.info("Upload ignorado por solicitacao --no-upload")
            elif not github_config.configurado:
                logger.warning(
                    "Upload ignorado: configure GITHUB_TOKEN, GITHUB_OWNER e GITHUB_REPO no .env"
                )
            else:
                GitHubClient(github_config, logger).publicar_json(conteudo_json)

            if not dados["faturamento"]["meta_disponivel"]:
                logger.warning(
                    "Metas de faturamento nao encontradas; configure-as em config.py"
                )
            logger.info("Execucao concluida com sucesso")
            return 0
    except ExecucaoEmAndamento as erro:
        logger.warning("Execucao encerrada: %s", erro)
        return 3
    except (ExcelReaderError, OSError, ValueError) as erro:
        logger.exception("Falha controlada na automacao: %s", erro)
        return 1
    except Exception:
        logger.exception("Erro inesperado na automacao")
        return 1
    finally:
        logger.info("Fim da execucao")


if __name__ == "__main__":
    raise SystemExit(main())
