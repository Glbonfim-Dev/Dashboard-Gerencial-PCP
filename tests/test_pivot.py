import unittest
from datetime import date
from producao_pivot import normalizar,classificar,montar_sql

class PivotTests(unittest.TestCase):
    def linha(self,**kw):
        r=dict(data_mes_grade=date(2026,11,18),segmento='MOLDE',cod_produto_proprio='P1',produto_proprio='MOLD FP RET GRID P/B',unidade='UN',qtde_utilizada=1,empresa_auditoria=1,os_id=1,id_linha_produto='A',descricao_conjunto='MOLD FP RET MOLDE COMPLETO')
        return {**r,**kw}
    def test_limite_atual_segmento_e_repeticao(self):
        r=self.linha();rows=[r,r,self.linha(data_mes_grade=date(2026,11,19)),self.linha(segmento='PECAS')]
        p=normalizar(rows,date(2026,11,18));self.assertEqual(len(p['registros']),1)
        self.assertEqual(p['fim'],'2026-11-18')
    def test_categorias_confirmadas(self):
        for name,cat in [('GRID PAVER','MOLDES_FP'),('FP16F P/B','MOLDES_FP'),('FC N14X39 GRID','MOLDES_FB'),('MF P/B','MOLDES_FB'),('FBEDESM P/B','MOLDES_FB'),('SPT #19','SAPATAS'),('SHOE ASSY','SAPATAS'),('CAST. C/PORT.SP','CASTELOS')]:
            self.assertEqual(classificar(name)[0],cat)
        self.assertEqual(classificar('CAV/SUP')[0],'AUXILIAR')
        self.assertEqual(classificar('HEATER,3X7CAST,600W')[0],'AUXILIAR')
        self.assertEqual(classificar('TERMO NOVO')[0],'PENDENTE')
    def test_saida_sem_identificadores_fiscais(self):
        r=normalizar([self.linha()],date(2026,11,18))['registros'][0]
        self.assertNotIn('nf',r);self.assertNotIn('cliente',r);self.assertNotIn('os_id',r)
        self.assertTrue(r['conjunto_id'])
    def test_quantidade_conflitante_impede_publicacao(self):
        with self.assertRaises(ValueError):normalizar([self.linha(),self.linha(qtde_utilizada=2)],date(2026,11,18))
    def test_consulta_so_leitura_e_data(self):
        sql=montar_sql(date(2026,11,18));self.assertIn("'2026-11-18'",sql)
        self.assertNotIn(':FtDate',sql);self.assertIn('LIMIT 20001',sql)
