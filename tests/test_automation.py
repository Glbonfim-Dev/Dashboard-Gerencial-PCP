from __future__ import annotations

import base64
import json
import logging
import unittest
from datetime import date, timedelta
from pathlib import Path

import requests
from openpyxl import Workbook

from config import ACOES_CONFIG, FATURAMENTO_CONFIG
from excel_reader import (
    calcular_indicadores,
    carregar_dados_excel,
    normalizar_status,
    numero,
)
from github_client import GitHubClient, GitHubConfig
from monitorar_excel import assinatura_arquivo, ler_estado, monitorar_uma_vez
from publicar_dashboard import (
    ExecucaoEmAndamento,
    ExecucaoLock,
    escrever_json_atomico,
    validar_caminho,
)


# Sessão HTTP controlada para testar o GitHub sem acessar a internet.
class FakeSession:
    def __init__(self, respostas: list[requests.Response]) -> None:
        self.headers: dict[str, str] = {}
        self.respostas = respostas
        self.chamadas: list[tuple[str, dict[str, object]]] = []

    def request(self, method: str, **kwargs: object) -> requests.Response:
        self.chamadas.append((method, kwargs))
        return self.respostas.pop(0)


def resposta(status: int, payload: dict[str, object]) -> requests.Response:
    """Cria uma resposta requests mínima usada nos testes da API."""

    resultado = requests.Response()
    resultado.status_code = status
    resultado._content = json.dumps(payload).encode("utf-8")
    resultado.headers["Content-Type"] = "application/json"
    return resultado


class AutomationTests(unittest.TestCase):
    """Testes das conversões, Excel, JSON, lock e cliente GitHub."""

    # As variações abaixo representam textos encontrados em planilhas reais.
    def test_normaliza_status_com_acentos_espacos_e_caixa(self) -> None:
        self.assertEqual(normalizar_status(" implementada  "), "Implementada")
        self.assertEqual(normalizar_status("IMPLEMENTADO"), "Implementada")
        self.assertEqual(normalizar_status("Em ANDAMENTO"), "Em Andamento")
        self.assertEqual(normalizar_status("não iniciada"), "Não Iniciada")
        self.assertEqual(normalizar_status("FALTA INICIAR "), "Não Iniciada")

    def test_converte_numeros_brasileiros(self) -> None:
        self.assertEqual(numero("R$ 1.234,56"), 1234.56)
        self.assertEqual(numero(10), 10.0)
        self.assertEqual(numero(None), 0.0)

    def test_le_planilha_e_calcula_indicadores(self) -> None:
        # A planilha temporária permite testar colunas sem usar o arquivo da rede.
        caminho = Path(__file__).parent / "_runtime_teste.xlsm"
        self.addCleanup(caminho.unlink, missing_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = ACOES_CONFIG.aba
        ws["F8"] = "Ação concluída"
        ws["G8"] = "Ana"
        ws["H8"] = date.today() - timedelta(days=10)
        ws["J8"] = " implementada "
        ws["F9"] = "Ação atrasada"
        ws["G9"] = "Bruno"
        ws["H9"] = date.today() - timedelta(days=1)
        ws["J9"] = "EM ANDAMENTO"
        fat = wb.create_sheet(FATURAMENTO_CONFIG.aba)
        fat["D15"] = "JANEIRO"
        fat["H15"] = 2500
        wb.save(caminho)

        logger = logging.getLogger("teste_excel_reader")
        acoes, mensal = carregar_dados_excel(caminho, logger)
        dados = calcular_indicadores(acoes, mensal, caminho.name)

        self.assertEqual(dados["acoes"]["total"], 2)
        self.assertEqual(dados["acoes"]["implementadas"], 1)
        self.assertEqual(dados["acoes"]["atrasadas"], 1)
        self.assertEqual(dados["faturamento"]["realizado_total"], 2500.0)
        self.assertIn("referencia_mensal", dados["faturamento"])

    def test_json_atomico_preserva_unicode_e_tipos(self) -> None:
        destino = Path(__file__).parent / "_runtime_dados.json"
        temporario = destino.with_suffix(".json.tmp")
        self.addCleanup(destino.unlink, missing_ok=True)
        self.addCleanup(temporario.unlink, missing_ok=True)
        escrever_json_atomico({"ação": "Revisão", "valor": 12.5}, destino)
        texto = destino.read_text(encoding="utf-8")
        self.assertIn("Revisão", texto)
        self.assertIsInstance(json.loads(texto)["valor"], float)
        self.assertFalse(temporario.exists())

    def test_validacao_de_extensao(self) -> None:
        with self.assertRaisesRegex(ValueError, "extensao"):
            validar_caminho("arquivo.csv")

    def test_lock_impede_execucao_concorrente_e_e_removido(self) -> None:
        lock = Path(__file__).parent / "_runtime_dashboard.lock"
        self.addCleanup(lock.unlink, missing_ok=True)
        with ExecucaoLock(lock):
            with self.assertRaises(ExecucaoEmAndamento):
                with ExecucaoLock(lock):
                    self.fail("o segundo lock nao deveria ser adquirido")
        self.assertFalse(lock.exists())

    def test_monitor_publica_apenas_quando_excel_muda(self) -> None:
        excel = Path(__file__).parent / "_runtime_monitor_origem.xlsm"
        estado = Path(__file__).parent / "_runtime_monitor_estado.json"
        self.addCleanup(excel.unlink, missing_ok=True)
        self.addCleanup(estado.unlink, missing_ok=True)
        self.addCleanup(estado.with_suffix(".json.tmp").unlink, missing_ok=True)
        excel.write_bytes(b"primeira versao")
        chamadas: list[Path] = []

        def publicador(caminho: Path) -> int:
            chamadas.append(caminho)
            return 0

        self.assertEqual(
            monitorar_uma_vez(
                excel, estado, espera_estabilidade=0, publicador=publicador
            ),
            0,
        )
        self.assertEqual(chamadas, [excel])
        self.assertEqual(ler_estado(estado), assinatura_arquivo(excel))

        self.assertEqual(
            monitorar_uma_vez(
                excel, estado, espera_estabilidade=0, publicador=publicador
            ),
            0,
        )
        self.assertEqual(chamadas, [excel])

        excel.write_bytes(b"segunda versao com tamanho diferente")
        self.assertEqual(
            monitorar_uma_vez(
                excel, estado, espera_estabilidade=0, publicador=publicador
            ),
            0,
        )
        self.assertEqual(chamadas, [excel, excel])

    def test_monitor_nao_grava_estado_quando_publicacao_falha(self) -> None:
        excel = Path(__file__).parent / "_runtime_monitor_falha.xlsm"
        estado = Path(__file__).parent / "_runtime_monitor_falha_estado.json"
        self.addCleanup(excel.unlink, missing_ok=True)
        self.addCleanup(estado.unlink, missing_ok=True)
        excel.write_bytes(b"conteudo")

        codigo = monitorar_uma_vez(
            excel,
            estado,
            espera_estabilidade=0,
            publicador=lambda _: 1,
        )

        self.assertEqual(codigo, 1)
        self.assertFalse(estado.exists())

    def test_github_cria_arquivo_quando_nao_existe(self) -> None:
        # GET 404 seguido de PUT 201 representa a primeira publicação.
        sessao = FakeSession([resposta(404, {"message": "Not Found"}), resposta(201, {"content": {}})])
        cliente = GitHubClient(
            GitHubConfig("token-secreto", "empresa", "dashboard"),
            logging.getLogger("teste_github"),
            session=sessao,
        )
        cliente.publicar_json(b'{"ok": true}\n')
        self.assertEqual([c[0] for c in sessao.chamadas], ["GET", "PUT"])
        payload = sessao.chamadas[1][1]["json"]
        self.assertEqual(base64.b64decode(payload["content"]), b'{"ok": true}\n')
        self.assertNotIn("sha", payload)

    def test_github_atualiza_com_sha(self) -> None:
        # Arquivos existentes precisam enviar novamente o SHA retornado pelo GET.
        sessao = FakeSession([resposta(200, {"sha": "abc123"}), resposta(200, {"content": {}})])
        cliente = GitHubClient(
            GitHubConfig("token-secreto", "empresa", "dashboard", json_path="docs/dados.json"),
            logging.getLogger("teste_github_sha"),
            session=sessao,
        )
        cliente.publicar_json(b"{}")
        payload = sessao.chamadas[1][1]["json"]
        self.assertEqual(payload["sha"], "abc123")
        self.assertTrue(sessao.chamadas[0][1]["url"].endswith("/docs/dados.json"))


if __name__ == "__main__":
    unittest.main()
