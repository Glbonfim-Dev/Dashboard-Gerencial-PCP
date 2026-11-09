from __future__ import annotations

import base64
import json
import logging
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import requests
from openpyxl import Workbook

from config import ACOES_CONFIG, FATURAMENTO_CONFIG, QUALIDADE_CONFIG
from excel_reader import (
    calcular_indicadores,
    carregar_dados_excel,
    normalizar_status,
    numero,
    ler_qualidade,
    ler_faturamento,
    ExcelReaderError,
)
from github_client import GitHubClient, GitHubConfig
from monitorar_excel import assinatura_arquivo, ler_estado, monitorar_uma_vez
from publicar_dashboard import (
    ExecucaoEmAndamento,
    ExecucaoLock,
    escrever_json_atomico,
    validar_caminho,
    main as publicar,
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
        acoes, mensal, qualidade = carregar_dados_excel(caminho, logger)
        dados = calcular_indicadores(acoes, mensal, caminho.name)

        self.assertEqual(dados["acoes"]["total"], 2)
        self.assertEqual(dados["acoes"]["implementadas"], 1)
        self.assertEqual(dados["acoes"]["atrasadas"], 1)
        self.assertEqual(dados["faturamento"]["realizado_total"], 2500.0)
        self.assertIn("referencia_mensal", dados["faturamento"])
        self.assertFalse(qualidade["disponivel"])

    def test_metas_2026_aumentam_em_novembro_sem_alterar_realizado(self) -> None:
        wb = Workbook()
        self.addCleanup(wb.close)
        realizados = [500000.0] * 10 + [377000.0, 600000.0]
        meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
                 "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
        for linha, (mes, realizado) in enumerate(zip(meses, realizados), start=15):
            wb.active[f"D{linha}"] = mes
            wb.active[f"H{linha}"] = realizado
        mensal = ler_faturamento(wb.active)
        self.assertEqual([m["meta"] for m in mensal], [1000000.0] * 10 + [1200000.0] * 2)
        self.assertEqual([m["realizado"] for m in mensal], realizados)
        for mes in (10, 11, 12):
            with self.subTest(mes=mes), patch("excel_reader.datetime") as relogio:
                relogio.now.return_value = datetime(2026, mes, 9)
                fat = calcular_indicadores([], mensal, "teste.xlsx")["faturamento"]
                self.assertEqual(fat["meta_total"], 12400000.0)
                self.assertEqual(fat["realizado_total"], sum(realizados))
                self.assertEqual(fat["percentual_atingimento"], round(sum(realizados) / 12400000 * 100, 2))
                meta = 1000000.0 if mes == 10 else 1200000.0
                self.assertEqual(fat["referencia_mensal"]["meta"], meta)
                self.assertEqual(fat["referencia_mensal"]["percentual_atingimento"], round(realizados[mes - 1] / meta * 100, 2))

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

    def test_qualidade_reconhece_colunas_movidas_e_novos_campos(self) -> None:
        wb = Workbook()
        self.addCleanup(wb.close)
        ws = wb.active
        ws.append(["RNC INTERNA POR ÁREA"])
        ws.append(["Mês", "ENGENHARIA", "OPERAÇÃO"])
        ws.append([date(2026, 1, 1), 2, 28])
        ws.append([date(2026, 2, 1), 12, 32])
        ws.append(["TOTAL", 14, 60])
        original = ler_qualidade(ws)
        ws.insert_rows(1, 5)
        ws.insert_cols(1, 3)
        movido = ler_qualidade(ws)
        self.assertEqual(movido, original)
        ws.insert_cols(5)
        ws["E7"] = "INSPEÇÃO"
        ws["E8"] = 3
        ws["E9"] = 0
        campos = ler_qualidade(ws)["indicadores"][0]
        self.assertIn("INSPEÇÃO", [c["rotulo"] for c in campos["campos"]])
        self.assertEqual(campos["mensal"][0]["valores"]["inspecao"], 3)
        self.assertEqual(campos["mensal"][1]["valores"]["inspecao"], 0)

    def test_qualidade_distingue_vazios_zero_erros_percentuais_e_anos(self) -> None:
        wb = Workbook()
        self.addCleanup(wb.close)
        ws = wb.active
        for row in [
            ["RECLAMAÇÃO DE CLIENTE (ORIGEM)"],
            ["Mês", "QTD RNC", "CLIENTE", "%", "META <"],
            [date(2025, 1, 1), 20, 2, 0.1, 0],
            [date(2026, 1, 1), 10, 0, 0, 0],
            [date(2026, 2, 1), None, None, "#DIV/0!", 0],
            ["TOTAL", 30, 2],
        ]:
            ws.append(row)
        resultado = ler_qualidade(ws)
        bloco = resultado["indicadores"][0]
        self.assertEqual(bloco["tipo"], "clientes")
        self.assertEqual([r["ano"] for r in bloco["mensal"]], [2025, 2026, 2026])
        self.assertEqual(bloco["mensal"][0]["valores"]["%"], 10)
        self.assertEqual(bloco["mensal"][1]["valores"]["cliente"], 0)
        self.assertIsNone(bloco["mensal"][2]["valores"]["cliente"])
        self.assertIsNone(bloco["mensal"][2]["valores"]["%"])
        self.assertEqual(len(resultado["avisos"]), 1)

    def test_qualidade_converte_horas_acima_de_24_e_mantem_custos(self) -> None:
        wb = Workbook()
        self.addCleanup(wb.close)
        ws = wb.active
        for row in [
            ["Mês", "Hrs Gastas"],
            [date(2026, 1, 1), timedelta(days=2, hours=3, minutes=30)],
            [date(2026, 2, 1), time(6, 30)],
            ["TOTAL"],
            ["Mês", "CUSTO R$"],
            [date(2026, 1, 1), 1234.56],
            ["TOTAL"],
        ]:
            ws.append(row)
        blocos = ler_qualidade(ws)["indicadores"]
        self.assertEqual(blocos[0]["mensal"][0]["valores"]["hrs_gastas"], 51.5)
        self.assertEqual(blocos[0]["mensal"][1]["valores"]["hrs_gastas"], 6.5)
        self.assertEqual(blocos[1]["mensal"][0]["valores"]["custo_r$"], 1234.56)

    def test_qualidade_detecta_mes_duplicado_e_estrutura_invalida(self) -> None:
        wb = Workbook()
        self.addCleanup(wb.close)
        ws = wb.active
        ws.append(["Dados sem cabeçalhos"])
        with self.assertRaises(ExcelReaderError):
            ler_qualidade(ws)
        ws.append(["Mês", "QTD RNC"])
        ws.append([date(2026, 1, 1), 3])
        ws.append([date(2026, 1, 1), 4])
        with self.assertRaisesRegex(ExcelReaderError, "duplicado"):
            ler_qualidade(ws)

    def test_salvamento_qualidade_chega_ao_json_sem_upload(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parent, prefix="_runtime_") as pasta:
            raiz = Path(pasta)
            excel, destino, estado = raiz / "fonte.xlsx", raiz / "dados.json", raiz / "estado.json"
            wb = Workbook()
            self.addCleanup(wb.close)
            wb.active.title = ACOES_CONFIG.aba
            wb.active["F8"] = "Ação preservada"
            fat = wb.create_sheet(FATURAMENTO_CONFIG.aba)
            fat["D15"], fat["H15"] = "JANEIRO", 2500
            ws = wb.create_sheet(QUALIDADE_CONFIG.aba)
            ws.append(["RNC TOTAL"])
            ws.append(["Mês", "QTD RNC", "META <"])
            ws.append([date(2026, 1, 1), 38, 0])
            wb.save(excel)

            with patch("publicar_dashboard.JSON_OUTPUT_PATH", destino), patch("publicar_dashboard.LOCK_PATH", raiz / "lock"), patch.object(GitHubClient, "publicar_json") as upload:
                def publicador(caminho: Path) -> int:
                    return publicar([str(caminho), "--no-upload"])

                self.assertEqual(monitorar_uma_vez(excel, estado, espera_estabilidade=0, publicador=publicador), 0)
                antes = json.loads(destino.read_text(encoding="utf-8"))
                self.assertEqual(antes["qualidade"]["indicadores"][0]["mensal"][0]["valores"]["qtd_rnc"], 38)
                ws.insert_cols(2)
                ws["C3"] = 45
                wb.save(excel)
                self.assertEqual(monitorar_uma_vez(excel, estado, espera_estabilidade=0, publicador=publicador), 0)
                depois = json.loads(destino.read_text(encoding="utf-8"))
                self.assertEqual(depois["qualidade"]["indicadores"][0]["mensal"][0]["valores"]["qtd_rnc"], 45)
                self.assertEqual(antes["faturamento"], depois["faturamento"])
                self.assertEqual(antes["acoes"], depois["acoes"])
                upload.assert_not_called()

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
