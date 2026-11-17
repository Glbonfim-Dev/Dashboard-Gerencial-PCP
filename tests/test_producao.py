import unittest
from openpyxl import Workbook
from producao_reader import ler_linhas

class ProducaoTests(unittest.TestCase):
    def sheet(self, rows):
        ws = Workbook().active
        for row in rows: ws.append(row)
        return ws

    def test_base_manual_componentes_e_materiais(self):
        headers = ['nota_fiscal','emissao_nf','descricao_nf','os_principal',
                   'cod_produto_proprio','produto_proprio','qtde_utilizada','os_fabricacao',
                   'cod_material_fabricacao']
        ws = self.sheet([headers,
            [10,'22/01/2026','MOLDE COMPLETO',100,'C1','MOLD HTX700 CAST. C/PORT.SP',1,101,'M1'],
            [10,'22/01/2026','MOLDE COMPLETO',100,'C1','MOLD HTX700 CAST. C/PORT.SP',1,101,'M2'],
            [10,'22/01/2026','MOLDE COMPLETO',100,'S1','MOLD HTX700 SPT',10,102,None],
            [11,'23/01/2026','MOLDE COMPLETO',100,'S1','MOLD HTX700 SPT',10,102,None],
            [12,'23/01/2025','MOLDE COMPLETO',100,'S1','MOLD HTX700 SPT',10,102,None]])
        rows = ler_linhas(ws)
        self.assertEqual(len(rows),3)
        self.assertEqual(sum(r['quantidade'] for r in rows if r['componente']=='CASTELO'),1)
        self.assertEqual(sum(r['quantidade'] for r in rows if r['componente']=='SAPATA'),20)
        self.assertEqual({r['os_molde_completo'] for r in rows},{'100'})

    def test_utilizacoes_distintas_sem_material_preservadas(self):
        ws = self.sheet([['nota_fiscal','emissao_nf','produto_proprio','qtde_utilizada'],
                         [45,'27/05/2026','GROMMET',20],
                         [45,'27/05/2026','GROMMET',30],
                         [45,'27/05/2026','GROMMET',18]])
        self.assertEqual(sum(r['quantidade'] for r in ler_linhas(ws)),68)

    def test_quantidade_e_cfop_preservados(self):
        ws = self.sheet([['mes_ref','tipo_componente','quantidade','cfop','descricao_original'],
                         ['2026-10','SAPATA',40,6101,'SHOE ASSY'],
                         ['2026-10','CASTELO',1,6922,'CASTELO']])
        rows = ler_linhas(ws)
        self.assertEqual(sum(r['quantidade'] for r in rows), 41)
        self.assertEqual(rows[1]['cfop'], '6922')

    def test_aba_vazia_nao_inventa_zero(self):
        self.assertEqual(ler_linhas(Workbook().active), [])

    def test_quantidade_ausente_falha(self):
        ws = self.sheet([['mes_ref','tipo_componente','quantidade'],['2026-10','CASTELO',None]])
        with self.assertRaises(ValueError): ler_linhas(ws)

    def test_mes_invalido_falha(self):
        ws = self.sheet([['mes_ref','tipo_componente','quantidade'],['2026-13','CASTELO',1]])
        with self.assertRaises(ValueError): ler_linhas(ws)

    def test_matriz_mensal_e_restricao_2026(self):
        ws = self.sheet([['mes_ref', 'CASTELO', 'SAPATA', 'periodo_parcial'],
                         ['2025-12', 8, 100, 'N'], ['2026-10', 1, 283, 'N'],
                         ['2026-11', 0, 0, 'S']])
        rows = ler_linhas(ws)
        self.assertEqual([(r['mes_ref'],r['componente'],r['quantidade']) for r in rows],
                         [('2026-10','CASTELO',1),('2026-10','SAPATA',283)])
        self.assertTrue(all(not r['cfop'] for r in rows))

    def test_coluna_sem_titulo_nao_perde_quantidade(self):
        ws = self.sheet([['mes_ref', None, 'CASTELO'], ['2026-01', 51, 0]])
        rows = ler_linhas(ws)
        self.assertEqual(rows[0]['quantidade'], 51)
        self.assertIn('SEM CLASSIFICAÇÃO', rows[0]['componente'])
