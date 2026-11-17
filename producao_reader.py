"""Leitura de Produção - KPI da planilha principal. Nunca grava no Excel."""
import math
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook
from excel_reader import chave_texto

ANO = '2026'

def ler_producao(caminho: Path) -> dict:
    registros, meses_parciais = [], []
    avisos = [
        'Resultados vinculados às notas, não produção concluída. Compare unidades dentro de cada componente.',
        'O preenchimento e a validação da planilha são manuais. O dashboard atualiza a leitura dos dados salvos automaticamente.',
    ]
    wb = load_workbook(caminho, read_only=True, data_only=True, keep_links=False)
    consolidado = False
    estrutura_nf = False
    try:
        nome = next((n for n in wb.sheetnames if chave_texto(n) == 'PRODUCAO - KPI'), None)
        if nome:
            ws = wb[nome]
            headers = [chave_texto(c.value).lower().replace(' ', '_') for c in next(ws.iter_rows())]
            estrutura_nf = 'produto_proprio' in headers and 'emissao_nf' in headers
            consolidado = 'mes_ref' in headers and 'tipo_componente' not in headers
            registros = ler_linhas(ws)
            if consolidado:
                avisos.append('Fonte consolidada por mês e componente: não há detalhe por modelo, nota ou CFOP. Ranking e recorrência são por componente.')
                for row in ws.iter_rows(values_only=True):
                    if str(row[0]).startswith(ANO+'-') and str(row[-1]).upper() == 'S':
                        meses_parciais.append(str(row[0]))
            if estrutura_nf:
                avisos.append('Quantidades de componentes vêm de qtde_utilizada. Materiais de fabricação não são somados a esses componentes. O cartão de moldes conta OS principais distintas com descrição de conjunto completo, não unidades fiscais de moldes.')
        if not registros:
            avisos.append('A aba Produção - KPI não contém quantidades reconhecidas de 2026.')
    finally:
        wb.close()
    return {
        'disponivel': bool(registros), 'origem': f'{caminho.name} · Produção - KPI',
        'registros': registros, 'meses': sorted({r['mes_ref'] for r in registros}),
        'meses_parciais': meses_parciais, 'granularidade': 'componente' if consolidado else 'item',
        'formato': 'estrutura_nf' if estrutura_nf else 'mensal',
        'operacao_disponivel': bool(registros) and all(r['cfop'] for r in registros),
        'avisos': avisos,
        'data_base': datetime.fromtimestamp(caminho.stat().st_mtime).isoformat(timespec='seconds'),
    }

def quantidade(value, ws, line):
    if value is None or isinstance(value, bool):
        raise ValueError(f'Quantidade ausente em {ws.title}, linha {line}')
    try:
        number = float(str(value).replace(',', '.'))
    except (ValueError, TypeError) as exc:
        raise ValueError(f'Quantidade inválida em {ws.title}, linha {line}') from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f'Quantidade inválida em {ws.title}, linha {line}')
    return number

def ler_linhas(ws):
    """Lê a matriz mensal existente ou tabela de itens, somente de 2026."""
    headers, result = None, []
    for index, row in enumerate(ws.iter_rows(values_only=True), 1):
        names = [chave_texto(v).lower().replace(' ', '_') for v in row]
        if headers is None:
            if 'produto_proprio' in names and 'emissao_nf' in names:
                return ler_estrutura(ws)
            if 'mes_ref' in names:
                headers = names
                named = [n for n in headers if n]
                if len(set(named)) != len(named):
                    raise ValueError(f'Cabeçalhos repetidos em {ws.title}')
            elif index >= 30:
                break
            continue
        if all(v is None for v in row):
            continue
        data = dict(zip(headers, row))
        month = str(data.get('mes_ref') or '')[:7]
        try:
            datetime.strptime(month, '%Y-%m')
        except ValueError as exc:
            raise ValueError(f'Mês inválido em {ws.title}, linha {index}') from exc
        if not month.startswith(ANO+'-'):
            continue
        if 'tipo_componente' not in headers:
            for column, (header, value) in enumerate(zip(headers, row), 1):
                if header in ('mes_ref', 'periodo_parcial') or value is None:
                    continue
                component = header.replace('_', ' ').upper() if header else f'SEM CLASSIFICAÇÃO (COLUNA {column})'
                qty = quantidade(value, ws, index)
                if qty > 0:
                    result.append(registro(month, component, qty))
        else:
            qty = quantidade(data.get('quantidade'), ws, index)
            component = str(data.get('tipo_componente') or 'SEM CLASSIFICAÇÃO').strip()
            result.append(registro(month, component, qty, data))
    return result


def componente_descricao(description):
    import re
    text = chave_texto(description)
    patterns = [
        ('MOLDE COMPLETO', r'\b(?:MOLDE COMPLETO|KIT COMPLETO|COMPLETO|COMPLET|COMPLETA)$'),
        ('CASTELO', r'\bCAST(?:ELO)?(?:\.|\s|$)'),
        ('GRADE', r'\bGRID\b|\bP/B\b'),
        ('SAPATA', r'\bSHOE\b|\bSPT\b|\bSAPATA\b'),
        ('AGITADOR', r'\bAGITADOR\b'), ('RASPADOR', r'\bRASPADOR\b|SCRAPE OFF'),
        ('CAVALETE SUPERIOR', r'CAV/SUP'),
    ]
    for name, pattern in patterns:
        if re.search(pattern, text): return name
    for name in ['END LINER','END PLATE','HEAD PLATE','HEAD PLUNGER','PLUNGERS',
                 'HD SP/MANIFOLD','RESIST FUND 600','RTD ASSY','INSULATING SPAC',
                 'GROMMET','MOLD STRAP','PORT/S','B.MESTR']:
        if name in text: return name
    return 'OUTROS COMPONENTES'


def ler_estrutura(ws):
    """Uma ocorrência por NF/OS/produto; materiais não multiplicam o produto pai.

    Notas distintas são preservadas; não inferir quantidade fiscal do conjunto
    a partir da quantidade de componentes da estrutura.
    """
    headers = None
    records = {}
    for index, row in enumerate(ws.iter_rows(values_only=True),1):
        names = [chave_texto(v).lower().replace(' ', '_') for v in row]
        if headers is None:
            if {'nota_fiscal','emissao_nf','produto_proprio','qtde_utilizada'}.issubset(names): headers = names
            continue
        if all(v is None for v in row): continue
        data = dict(zip(headers,row))
        value = data.get('emissao_nf')
        if isinstance(value, datetime): month = value.strftime('%Y-%m')
        elif hasattr(value,'strftime'): month = value.strftime('%Y-%m')
        else:
            parsed = None
            for fmt in ('%d/%m/%Y','%Y-%m-%d','%d/%m/%Y %H:%M:%S'):
                try: parsed = datetime.strptime(str(value).strip(),fmt);break
                except ValueError: pass
            if parsed is None: raise ValueError(f'Data de emissão inválida em {ws.title}, linha {index}')
            month = parsed.strftime('%Y-%m')
        if not month.startswith(ANO+'-'): continue
        qty = quantidade(data.get('qtde_utilizada'),ws,index)
        desc = str(data.get('produto_proprio') or '').strip()
        if not desc: raise ValueError(f'Produto próprio ausente em {ws.title}, linha {index}')
        code = str(data.get('cod_produto_proprio') or desc).strip()
        nf = str(data.get('nota_fiscal') or '').strip()
        os = str(data.get('os_principal') or '').strip()
        fab = str(data.get('os_fabricacao') or '').strip()
        key = (nf,os,code,fab)
        rec = registro(month,componente_descricao(desc),qty,{'descricao_original':desc,'chave_molde':code})
        rec.update(nf=nf,os_principal=os,os_fabricacao=fab,codigo_produto=code,
                   descricao_nf=str(data.get('descricao_nf') or ''),unidade=str(data.get('unidade') or ''))
        rec['os_molde_completo'] = os if componente_descricao(rec['descricao_nf'])=='MOLDE COMPLETO' else ''
        material = data.get('cod_material_fabricacao') or data.get('material_fabricacao')
        # Sem material, cada linha manual representa uma utilização própria.
        # Com material, colapsar apenas repetições idênticas do produto pai.
        unique = (key, tuple(sorted(rec.items()))) if material else (key, index)
        records.setdefault(unique, rec)
    return list(records.values())

def registro(month, component, qty, data=None):
    data = data or {}
    description = str(data.get('descricao_original') or component)
    return {
        'mes_ref': month, 'componente': component, 'quantidade': qty,
        'descricao': description, 'chave_molde': str(data.get('chave_molde') or description),
        'cfop': str(data.get('cfop_num') or data.get('cfop') or '').removesuffix('.0'),
    }
