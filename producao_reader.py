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
        'Quantidades faturadas, não produção concluída. Compare unidades dentro de cada componente.',
        'Castelos incorporados aos moldes completos não são contados separadamente.',
        'A planilha é atualizada somente mediante solicitação. O dashboard apenas lê os dados salvos.',
    ]
    wb = load_workbook(caminho, read_only=True, data_only=True, keep_links=False)
    consolidado = False
    try:
        nome = next((n for n in wb.sheetnames if chave_texto(n) == 'PRODUCAO - KPI'), None)
        if nome:
            ws = wb[nome]
            headers = [chave_texto(c.value).lower().replace(' ', '_') for c in next(ws.iter_rows())]
            consolidado = 'mes_ref' in headers and 'tipo_componente' not in headers
            registros = ler_linhas(ws)
            if consolidado:
                avisos.append('Fonte consolidada por mês e componente: não há detalhe por modelo, nota ou CFOP. Ranking e recorrência são por componente.')
                for row in ws.iter_rows(values_only=True):
                    if str(row[0]).startswith(ANO+'-') and str(row[-1]).upper() == 'S':
                        meses_parciais.append(str(row[0]))
        if not registros:
            avisos.append('A aba Produção - KPI não contém quantidades reconhecidas de 2026.')
    finally:
        wb.close()
    return {
        'disponivel': bool(registros), 'origem': f'{caminho.name} · Produção - KPI',
        'registros': registros, 'meses': sorted({r['mes_ref'] for r in registros}),
        'meses_parciais': meses_parciais, 'granularidade': 'componente' if consolidado else 'item',
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

def registro(month, component, qty, data=None):
    data = data or {}
    description = str(data.get('descricao_original') or component)
    return {
        'mes_ref': month, 'componente': component, 'quantidade': qty,
        'descricao': description, 'chave_molde': str(data.get('chave_molde') or description),
        'cfop': str(data.get('cfop_num') or data.get('cfop') or '').removesuffix('.0'),
    }
