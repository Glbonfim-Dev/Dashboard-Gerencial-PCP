"""Leitura do Excel e calculo dos dados publicados no dashboard."""

from __future__ import annotations

import logging
import math
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from config import (
    ACOES_CONFIG,
    EXCEL_INTERVALO_SEGUNDOS,
    EXCEL_MAX_TENTATIVAS,
    FATURAMENTO_CONFIG,
    VENCIMENTO_PROXIMO_DIAS,
    AcoesConfig,
    FaturamentoConfig,
)


class ExcelReaderError(RuntimeError):
    """Erro controlado ao acessar ou interpretar a planilha."""


# ---------------------------------------------------------------------------
# Normalização e conversão de valores
# ---------------------------------------------------------------------------

def normalizar_texto(valor: Any) -> str:
    """Remove espaços extras e converte valores vazios em texto vazio."""

    return " ".join(str(valor or "").strip().split())


def chave_texto(valor: Any) -> str:
    """Cria uma chave sem acentos e em maiúsculas para comparações seguras."""

    texto = normalizar_texto(valor).upper()
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def normalizar_status(valor: Any) -> str:
    """Agrupa diferentes escritas do Excel nos três status do dashboard."""

    chave = chave_texto(valor)
    if chave in {"IMPLEMENTADO", "IMPLEMENTADA", "CONCLUIDO", "CONCLUIDA"}:
        return "Implementada"
    if chave in {"EM ANDAMENTO", "ANDAMENTO", "EM EXECUCAO"}:
        return "Em Andamento"
    if chave in {
        "FALTA INICIAR",
        "NAO INICIADO",
        "NAO INICIADA",
        "NAO INICIADAS",
        "A INICIAR",
    }:
        return "Não Iniciada"
    return normalizar_texto(valor).title() or "Não Informado"


def numero(valor: Any) -> float:
    """Converte números do Excel ou textos em formato brasileiro para float."""

    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float)):
        resultado = float(valor)
        return resultado if math.isfinite(resultado) else 0.0

    texto = normalizar_texto(valor).replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        resultado = float(texto)
        return resultado if math.isfinite(resultado) else 0.0
    except ValueError:
        return 0.0


def data_iso(valor: Any) -> str | None:
    """Converte datas válidas para AAAA-MM-DD; demais valores retornam None."""

    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str):
        texto = normalizar_texto(valor)
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, formato).date().isoformat()
            except ValueError:
                continue
    return None


def aguardar_arquivo_disponivel(
    caminho: Path,
    logger: logging.Logger,
    max_tentativas: int = EXCEL_MAX_TENTATIVAS,
    intervalo: float = EXCEL_INTERVALO_SEGUNDOS,
) -> None:
    """Aguarda o arquivo existir e aceitar uma leitura basica."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, max_tentativas + 1):
        try:
            with caminho.open("rb") as arquivo:
                assinatura = arquivo.read(4)
            if assinatura != b"PK\x03\x04":
                raise ExcelReaderError("o arquivo nao possui uma assinatura XLSX/XLSM valida")
            logger.info("Excel disponivel para leitura na tentativa %d", tentativa)
            return
        except (OSError, ExcelReaderError) as erro:
            ultimo_erro = erro
            logger.warning(
                "Tentativa %d/%d de acesso ao Excel falhou: %s",
                tentativa,
                max_tentativas,
                erro,
            )
            if tentativa < max_tentativas:
                time.sleep(intervalo)

    raise ExcelReaderError(
        f"nao foi possivel acessar o Excel apos {max_tentativas} tentativas: {ultimo_erro}"
    )


# ---------------------------------------------------------------------------
# Leitura das abas configuradas
# ---------------------------------------------------------------------------

def _valor_coluna(ws: Any, coluna: str | None, linha: int) -> Any:
    """Lê uma célula; colunas opcionais configuradas como None ficam vazias."""

    return ws[f"{coluna}{linha}"].value if coluna else None


def ler_acoes(ws: Any, config: AcoesConfig = ACOES_CONFIG) -> list[dict[str, Any]]:
    """Transforma as linhas da aba de ações em registros padronizados."""

    acoes: list[dict[str, Any]] = []
    hoje = date.today()

    for linha in range(config.linha_inicial, ws.max_row + 1):
        descricao = normalizar_texto(_valor_coluna(ws, config.coluna_acao, linha))
        if not descricao:
            continue

        responsavel = normalizar_texto(
            _valor_coluna(ws, config.coluna_responsavel, linha)
        ).upper() or "NÃO INFORMADO"
        valor_prazo = _valor_coluna(ws, config.coluna_prazo, linha)
        prazo_iso = data_iso(valor_prazo)
        prazo_data = date.fromisoformat(prazo_iso) if prazo_iso else None
        status = normalizar_status(_valor_coluna(ws, config.coluna_status, linha))
        implementada = status == "Implementada"
        # Uma ação implementada nunca é classificada como atrasada.
        atrasada = bool(prazo_data and prazo_data < hoje and not implementada)
        proxima_vencimento = bool(
            prazo_data
            and not implementada
            and hoje <= prazo_data <= hoje + timedelta(days=VENCIMENTO_PROXIMO_DIAS)
        )

        acoes.append(
            {
                "acao": descricao,
                "responsavel": responsavel,
                "prazo": prazo_iso,
                "prazo_texto": normalizar_texto(valor_prazo) if not prazo_iso else "",
                "status": status,
                "observacao": normalizar_texto(
                    _valor_coluna(ws, config.coluna_observacao, linha)
                ),
                "data_conclusao": data_iso(
                    _valor_coluna(ws, config.coluna_data_conclusao, linha)
                ),
                "ano": prazo_data.year if prazo_data else FATURAMENTO_CONFIG.ano,
                "atrasada": atrasada,
                "proxima_vencimento": proxima_vencimento,
            }
        )
    return acoes


def ler_faturamento(
    ws: Any, config: FaturamentoConfig = FATURAMENTO_CONFIG
) -> list[dict[str, Any]]:
    """Lê realizado e meta de cada mês na ordem da planilha."""

    mensal: list[dict[str, Any]] = []
    for linha in range(config.linha_inicial, config.linha_final + 1):
        mes_completo = normalizar_texto(_valor_coluna(ws, config.coluna_mes, linha)).upper()
        if not mes_completo:
            continue
        meta_excel = _valor_coluna(ws, config.coluna_meta, linha)
        meta = (
            numero(meta_excel)
            if config.coluna_meta
            else numero(config.metas_mensais.get(mes_completo, 0))
        )
        mensal.append(
            {
                "mes": mes_completo[:3].title(),
                "mes_completo": mes_completo.title(),
                "meta": meta,
                "realizado": numero(
                    _valor_coluna(ws, config.coluna_realizado, linha)
                ),
            }
        )
    return mensal


def carregar_dados_excel(
    caminho: Path, logger: logging.Logger
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Abre o arquivo uma única vez e devolve ações e faturamento."""

    logger.info("Iniciando leitura das abas do Excel")
    try:
        workbook = load_workbook(
            filename=caminho,
            read_only=True,
            data_only=True,
            keep_links=False,
        )
    except Exception as erro:
        raise ExcelReaderError(f"falha ao abrir a planilha: {erro}") from erro

    try:
        abas_necessarias = {ACOES_CONFIG.aba, FATURAMENTO_CONFIG.aba}
        ausentes = abas_necessarias.difference(workbook.sheetnames)
        if ausentes:
            raise ExcelReaderError(
                "abas obrigatorias nao encontradas: " + ", ".join(sorted(ausentes))
            )

        acoes = ler_acoes(workbook[ACOES_CONFIG.aba])
        logger.info("Aba '%s' lida: %d acoes", ACOES_CONFIG.aba, len(acoes))
        faturamento = ler_faturamento(workbook[FATURAMENTO_CONFIG.aba])
        logger.info(
            "Aba '%s' lida: %d meses", FATURAMENTO_CONFIG.aba, len(faturamento)
        )
        return acoes, faturamento
    finally:
        workbook.close()


# ---------------------------------------------------------------------------
# Consolidação dos indicadores e montagem do conteúdo do JSON
# ---------------------------------------------------------------------------

def calcular_indicadores(
    acoes: list[dict[str, Any]],
    mensal: list[dict[str, Any]],
    arquivo_origem: str,
) -> dict[str, Any]:
    """Calcula KPIs, responsáveis, faturamento e lista de atenção."""

    contagem_status = Counter(acao["status"] for acao in acoes)
    contagem_responsaveis = Counter(acao["responsavel"] for acao in acoes)
    total = len(acoes)
    implementadas = contagem_status["Implementada"]
    atrasadas = sum(bool(acao["atrasada"]) for acao in acoes)
    meta_total = round(sum(item["meta"] for item in mensal), 2)
    realizado_total = round(sum(item["realizado"] for item in mensal), 2)
    indice_mes_atual = datetime.now().month - 1
    mes_referencia = mensal[indice_mes_atual] if indice_mes_atual < len(mensal) else None
    meta_mes = round(numero(mes_referencia["meta"]), 2) if mes_referencia else 0.0
    realizado_mes = (
        round(numero(mes_referencia["realizado"]), 2) if mes_referencia else 0.0
    )

    # Ordena primeiro atrasadas, depois não iniciadas e próximas do vencimento.
    def prioridade(acao: dict[str, Any]) -> tuple[Any, ...]:
        return (
            0 if acao["atrasada"] else 1,
            0 if acao["status"] == "Não Iniciada" else 1,
            0 if acao["proxima_vencimento"] else 1,
            acao["prazo"] or "9999-12-31",
            acao["acao"],
        )

    atencao = sorted(
        (
            acao
            for acao in acoes
            if acao["atrasada"]
            or acao["status"] == "Não Iniciada"
            or acao["proxima_vencimento"]
        ),
        key=prioridade,
    )

    periodos = sorted({int(acao["ano"]) for acao in acoes} | {FATURAMENTO_CONFIG.ano})
    return {
        "ultima_atualizacao": datetime.now().astimezone().isoformat(timespec="seconds"),
        "arquivo_origem": Path(arquivo_origem).name,
        "periodos": periodos,
        "acoes": {
            "total": total,
            "implementadas": implementadas,
            "em_andamento": contagem_status["Em Andamento"],
            "nao_iniciadas": contagem_status["Não Iniciada"],
            "outros": total
            - implementadas
            - contagem_status["Em Andamento"]
            - contagem_status["Não Iniciada"],
            "atrasadas": atrasadas,
            "percentual_concluido": round(
                (implementadas / total * 100) if total else 0.0, 2
            ),
        },
        "responsaveis": [
            {"nome": nome, "quantidade": quantidade}
            for nome, quantidade in sorted(
                contagem_responsaveis.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "faturamento": {
            "ano": FATURAMENTO_CONFIG.ano,
            "meta_total": meta_total,
            "realizado_total": realizado_total,
            "percentual_atingimento": round(
                (realizado_total / meta_total * 100) if meta_total else 0.0, 2
            ),
            "meta_disponivel": meta_total > 0,
            "referencia_mensal": {
                "mes": mes_referencia["mes"] if mes_referencia else "",
                "mes_completo": mes_referencia["mes_completo"] if mes_referencia else "",
                "meta": meta_mes,
                "realizado": realizado_mes,
                "percentual_atingimento": round(
                    (realizado_mes / meta_mes * 100) if meta_mes else 0.0, 2
                ),
            },
            "mensal": mensal,
        },
        "acoes_atencao": atencao,
        "lista_acoes": acoes,
    }
