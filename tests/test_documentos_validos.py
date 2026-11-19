"""Integração SQL somente leitura: CPS_TEST_INTEGRACAO=1 para executar.

Os dados de teste são CTEs VALUES, sem criar tabelas nem alterar o CPS.
"""
import os
import unittest
from pathlib import Path


@unittest.skipUnless(os.getenv('CPS_TEST_INTEGRACAO') == '1', 'Integração CPS opcional')
class DocumentosValidosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from credencial_cps import ler_senha
        cls.conn = psycopg.connect(
            host='10.250.100.251', dbname='CPS', user='DevLeitura',
            password=ler_senha(), connect_timeout=8,
            options='-c default_transaction_read_only=on -c statement_timeout=30000')

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def consultar(self, documentos, itens, referencias, fim='2026-11-19'):
        from psycopg import sql
        # Chaves são deliberadamente iguais entre empresas para testar isolamento.
        cabecalhos = [(emp, '55', '1', '1', nf, None, data, 'cliente', cancel, status)
                      for emp,nf,data,cancel,status in documentos]
        produtos = [(emp,'55','1','1',nf,aut,None,None,None,cod,'produto',qtd,1,nat,cfop)
                    for emp,nf,aut,cod,qtd,nat,cfop in itens]
        refs = [(emp,'55','1','1',nf,'55','1','1',orig,data)
                for emp,nf,orig,data in referencias]
        def valores(rows):
            return sql.SQL(',').join(sql.SQL('({})').format(
                sql.SQL(',').join(sql.Literal(v) for v in row)) for row in rows)
        tabelas = sql.SQL('''WITH PARAMETROS AS (
            SELECT DATE '2026-01-01' AS DATA_INICIO, {}::DATE AS DATA_FIM),
            TNOTA_FISCAL(COD_EMPRESA,MODELO,SERIE,SUB_SERIE,NUMERO,NUMERO_NFSE,
                DT_EMISSAO,CLIENTE,CANCELADA,NFE_COD_STATUS) AS (VALUES {}),
            TNOTA_FISCAL_ITEM(COD_EMPRESA,MODELO,SERIE,SUB_SERIE,NUMERO_NF,AUT_,
                COD_ORCAMENTO,GUID_ORCAMENTO,COD_OS,COD_PRODUTO,PRODUTO,QTDE,
                TP_MOVIMENTO_DEPOSITO,NATUREZA_OP,CFOP) AS (VALUES {}),
            TNOTA_FISCAL_NFREF(COD_EMPRESA,MODELO,SERIE,SUB_SERIE,NUMERO_NF,
                NFREF_MODELO,NFREF_SERIE,NFREF_SUB_SERIE,NFREF_NUMERO_NF,NFREF_DT_EMISSAO)
                AS (VALUES {}),
        ''').format(sql.Literal(fim), valores(cabecalhos), valores(produtos), valores(refs))
        regras = (Path(__file__).resolve().parents[1] /
                  'consultas/producao_documentos_validos.sql').read_text(encoding='utf-8').rstrip().rstrip(',')
        with self.conn.cursor() as cur:
            cur.execute(tabelas + sql.SQL(regras) + sql.SQL('''
                SELECT COD_EMPRESA,AUT_,QTDE_REMANESCENTE,FATOR_REMANESCENTE
                FROM ITENS_PRODUCAO_VALIDOS ORDER BY COD_EMPRESA,AUT_'''))
            return cur.fetchall()

    def test_cancelada_inutilizada_devolvida_e_nova_nota(self):
        from datetime import datetime as D
        dia=D(2026,10,7)
        docs=[(1,1,dia,0,'100'),(1,2,dia,0,'100'),(1,3,D(2026,10,14),0,'100'),
              (1,4,dia,1,'101'),(1,5,dia,0,'102'),(2,1,dia,0,'100')]
        itens=[(1,1,10,100,40,'VENDA','6101'),(1,2,20,100,40,'VENDA','6101'),
               (1,3,30,100,40,'DEVOLUÇÃO DE VENDA','1201'),
               (1,4,40,200,16,'VENDA','6101'),(1,5,50,300,15,'VENDA','6922'),
               (2,1,60,100,40,'VENDA','6101')]
        # Referência duplicada não pode dobrar a devolução.
        refs=[(1,3,1,dia),(1,3,1,dia)]
        self.assertEqual(self.consultar(docs,itens,refs),[(1,20,40,1),(2,60,40,1)])

    def test_devolucao_parcial_e_cancelada_e_futura(self):
        from datetime import datetime as D
        dia=D(2026,10,1)
        docs=[(1,1,dia,0,'100'),(1,2,D(2026,10,2),0,'100'),
              (1,3,D(2026,10,3),1,'101'),(1,4,D(2026,12,1),0,'100')]
        itens=[(1,1,10,100,40,'VENDA','6101'),
               (1,2,20,100,10,'DEVOLUÇÃO','1201'),
               (1,3,30,100,20,'DEVOLUÇÃO','1201'),
               (1,4,40,100,10,'DEVOLUÇÃO','1201')]
        refs=[(1,n,1,dia) for n in (2,3,4)]
        self.assertEqual(self.consultar(docs,itens,refs),[(1,10,30,0.75)])

    def test_devolucao_distribuida_sem_multiplicar_por_linha(self):
        from datetime import datetime as D
        dia=D(2026,10,1)
        docs=[(1,1,dia,0,'100'),(1,2,D(2026,10,2),0,'100')]
        itens=[(1,1,10,100,20,'VENDA','6101'),(1,1,11,100,20,'VENDA','6101'),
               (1,2,20,100,30,'DEVOLUÇÃO','1201')]
        self.assertEqual(self.consultar(docs,itens,[(1,2,1,dia)]),[(1,11,10,0.5)])
