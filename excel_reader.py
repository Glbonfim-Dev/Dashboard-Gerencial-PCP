"""Leitura do Excel e calculo dos dados publicados no dashboard."""

from __future__ import annotations

import logging
import math
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, time as hora, timedelta
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from config import (
    ACOES_CONFIG,
    EXCEL_INTERVALO_SEGUNDOS,
    EXCEL_MAX_TENTATIVAS,
    FATURAMENTO_CONFIG,
    QUALIDADE_CONFIG,
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


def _valor_qualidade(valor: Any, unidade: str) -> float | None:
    """Preserva ausências/erros e converte durações do Excel em horas decimais."""

    if valor is None or valor == "" or isinstance(valor, bool):
        return None
    if isinstance(valor, str) and valor.startswith("#"):
        return None
    if unidade == "horas":
        if isinstance(valor, timedelta):
            return round(valor.total_seconds() / 3600, 6)
        if isinstance(valor, hora):
            return round(valor.hour + valor.minute / 60 + valor.second / 3600, 6)
        # Datas de duração do Excel são frações de um dia.
        if isinstance(valor, (int, float)):
            return round(numero(valor) * 24, 6)
    if isinstance(valor, str):
        texto = valor.replace("R$", "").replace("%", "").strip().replace(" ", "")
        try:
            float(texto.replace(".", "").replace(",", ".") if "," in texto else texto)
        except ValueError:
            return None
    elif not isinstance(valor, (int, float)):
        return None
    return numero(valor) * (100 if unidade == "percentual" else 1)


def ler_qualidade(ws: Any) -> dict[str, Any]:
    """Descobre tabelas por Mês/cabeçalhos, incluindo novos campos e linhas movidas.

    Não soma percentuais, não mistura anos e não transforma células vazias em zero.
    Cada bloco conserva seus próprios dados, mesmo quando os totais não conciliam.
    """

    linhas = list(ws.iter_rows())

    def valor(linha: int, coluna: int) -> Any:
        return linhas[linha][coluna].value

    def cabecalho(linha: int, coluna: int) -> str:
        return normalizar_texto(valor(linha, coluna))

    indicadores: list[dict[str, Any]] = []
    avisos: list[str] = []
    ids: Counter[str] = Counter()
    for indice, linha in enumerate(linhas):
        meses = [col for col, celula in enumerate(linha) if chave_texto(celula.value) == "MES"]
        for posicao, coluna_mes in enumerate(meses):
            limite = meses[posicao + 1] if posicao + 1 < len(meses) else len(linha)
            colunas = [col for col in range(coluna_mes + 1, limite) if cabecalho(indice, col)]
            if not colunas:
                continue
            nomes = [chave_texto(cabecalho(indice, col)) for col in colunas]
            titulo = ""
            for anterior in range(indice - 1, max(-1, indice - 5), -1):
                texto = cabecalho(anterior, coluna_mes)
                if texto and isinstance(valor(anterior, coluna_mes), str) and chave_texto(texto) not in {"TOTAL", "MES"}:
                    titulo = texto
                    break
            # Os blocos de horas e custo não têm título na planilha original.
            if "QTD RNC" in nomes:
                tipo = next((nome.lower() + "s" for nome in ("CLIENTE", "FORNECEDOR", "INTERNA") if nome in nomes), "rnc_total")
                tipo = {"internas": "internas", "clientes": "clientes", "fornecedors": "fornecedores"}.get(tipo, tipo)
            elif any("HRS" in nome or "HORAS" in nome for nome in nomes):
                tipo = "horas" if len(colunas) == 1 else "horas_custos_maquinas"
            elif any("CUSTO" in nome for nome in nomes):
                tipo = "custo"
            elif "CUSTO" in chave_texto(titulo) or {"CMB", "FORNECEDOR", "CLIENTE"}.issubset(nomes):
                tipo = "custos_categoria"
            elif any("LASER" in nome for nome in nomes):
                tipo = "maquinas"
            elif "AREA" in chave_texto(titulo) or "ENGENHARIA" in nomes:
                tipo = "areas"
            else:
                tipo = chave_texto(titulo or " ".join(nomes)).lower().replace(" ", "_")
            titulo = titulo or {
                "horas": "Horas gastas", "custo": "Custo da qualidade",
                "horas_custos_maquinas": "Horas e custos por máquina",
            }.get(tipo, "Indicadores de qualidade")

            campos = []
            usados: Counter[str] = Counter()
            for col in colunas:
                rotulo = cabecalho(indice, col)
                nome = chave_texto(rotulo)
                unidade = (
                    "horas" if "HRS" in nome or "HORAS" in nome else
                    "moeda" if "R$" in nome or tipo == "custos_categoria" else
                    "percentual" if nome == "%" or ("META" in nome and "%" in nomes) else
                    "quantidade"
                )
                if nomes.count(nome) > 1:
                    # Cabeçalhos repetidos Hrs/R$ usam o grupo imediatamente acima.
                    grupo = next((cabecalho(indice - 1, c) for c in range(col, coluna_mes, -1)
                                  if indice > 0 and cabecalho(indice - 1, c)), "")
                    rotulo = f"{grupo} · {rotulo}" if grupo else rotulo
                chave = chave_texto(rotulo).lower().replace(" ", "_")
                usados[chave] += 1
                if usados[chave] > 1:
                    chave += f"_{usados[chave]}"
                campos.append({"chave": chave, "rotulo": rotulo, "unidade": unidade,
                               "meta": "META" in nome, "coluna": col})
            registros = []
            erros = 0
            datas_vistas: set[str] = set()
            for prox in range(indice + 1, len(linhas)):
                mes = valor(prox, coluna_mes)
                if chave_texto(mes) in {"TOTAL", "MES"}:
                    break
                iso = data_iso(mes)
                if not iso:
                    continue
                if iso in datas_vistas:
                    raise ExcelReaderError(f"mês duplicado no bloco de qualidade: {titulo} ({iso})")
                datas_vistas.add(iso)
                data = date.fromisoformat(iso)
                valores = {}
                for campo in campos:
                    bruto = valor(prox, campo["coluna"])
                    convertido = _valor_qualidade(bruto, campo["unidade"])
                    valores[campo["chave"]] = convertido
                    if bruto is not None and bruto != "" and convertido is None:
                        erros += 1
                registros.append({"ano": data.year, "mes": data.month, "valores": valores})
            if registros:
                ids[tipo] += 1
                identificador = tipo if ids[tipo] == 1 else f"{tipo}_{ids[tipo]}"
                indicadores.append({"id": identificador, "tipo": tipo, "titulo": titulo,
                                    "campos": [{k: v for k, v in c.items() if k != "coluna"} for c in campos],
                                    "mensal": sorted(registros, key=lambda m: (m["ano"], m["mes"]))})
                if erros:
                    avisos.append(f"{titulo}: {erros} células sem resultado válido no Excel; exibidas como sem dados.")
    if not indicadores:
        raise ExcelReaderError("a aba de qualidade não contém tabelas reconhecíveis com cabeçalho Mês")
    return {"disponivel": True, "ano": QUALIDADE_CONFIG.ano, "indicadores": indicadores, "avisos": avisos}


def carregar_dados_excel(
    caminho: Path, logger: logging.Logger
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Abre o arquivo uma única vez e devolve ações, faturamento e qualidade."""

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
        aba_qualidade = next(
            (nome for nome in workbook.sheetnames if chave_texto(nome) == chave_texto(QUALIDADE_CONFIG.aba)),
            None,
        )
        qualidade = ler_qualidade(workbook[aba_qualidade]) if aba_qualidade else {
            "disponivel": False, "ano": QUALIDADE_CONFIG.ano, "indicadores": [],
            "avisos": ["A aba Qualidade KPI 2026 não foi encontrada na planilha."],
        }
        logger.info("Qualidade: %d blocos de indicadores", len(qualidade["indicadores"]))
        return acoes, faturamento, qualidade
    finally:
        workbook.close()


# ---------------------------------------------------------------------------
# Consolidação dos indicadores e montagem do conteúdo do JSON
# ---------------------------------------------------------------------------

def calcular_indicadores(
    acoes: list[dict[str, Any]],
    mensal: list[dict[str, Any]],
    arquivo_origem: str,
    qualidade: dict[str, Any] | None = None,
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
        "qualidade": qualidade or {
            "disponivel": False, "ano": QUALIDADE_CONFIG.ano, "indicadores": [], "avisos": [],
        },
    }
