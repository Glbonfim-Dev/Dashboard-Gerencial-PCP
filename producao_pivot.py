"""Consulta CPS somente leitura. Saída pública sem números de NF/OS ou clientes."""
import hashlib
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from excel_reader import chave_texto

ROOT = Path(__file__).resolve().parent

def hoje():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()

def montar_sql(limite):
    s=(ROOT/'consultas/producao_pivot_base.sql').read_text(encoding='utf-8')
    s='\n'.join(s.splitlines())
    s=s.replace(':FtDateInicio',"'2026-01-01'").replace(':FtDateFim',f"'{limite.isoformat()}'")
    match=re.search(r'SELECT\s+COALESCE\(\s+NULLIF\(I.NUMERO_NFSE',s)
    if not match: raise ValueError('Definicao da grade mudou; revisar consulta')
    s=s[:match.start()]+s[match.start():].replace('SELECT','SELECT I.COD_EMPRESA AS EMPRESA_AUDITORIA, M.GUID_LINHA AS ID_LINHA_PRODUTO, OS.CODIGO AS OS_ID, I.DT_EMISSAO AS DATA_MES_GRADE, I.AUT_ITEM AS ID_ITEM_FATURADO, I.TIPO_ITEM AS TIPO_ITEM_FATURADO, I.QTDE_NF AS QUANTIDADE_FATURADA, I.COD_PRODUTO AS CODIGO_ITEM_FATURADO, M.COD_PRODUTO AS ID_CADASTRO_PROPRIO,',1)
    order=re.search(r'\nORDER BY\s+I.COD_EMPRESA',s)
    if not order: raise ValueError('Ordenacao da grade nao reconhecida')
    s=s[:order.start()].rstrip().rstrip(';')
    return '''SELECT q.data_mes_grade, q.segmento,q.cod_produto_proprio,
 q.produto_proprio,q.unidade,q.qtde_utilizada,q.empresa_auditoria,q.os_id,
 q.id_linha_produto,q.descricao_nf AS descricao_conjunto,
 q.id_item_faturado,q.tipo_item_faturado,q.quantidade_faturada,
 q.codigo_item_faturado,q.id_cadastro_proprio FROM ('''+s+'''
 ) q WHERE upper(trim(q.segmento)) IN ('MOLDE','MOLDES')
 ORDER BY data_mes_grade,os_id,id_linha_produto LIMIT 20001'''

def classificar(descricao, faturado=False):
    t=chave_texto(descricao)
    if re.search(r'\b(?:ENDCORE|COREBAR|CANECO)\b',t): return 'CANECOS','CANECO'
    if re.search(r'\bCAST(?:ELO)?(?:\.|\s|$)',t): return 'CASTELOS','CASTELO'
    if re.search(r'\bSPT\b|\bSHOE\b|\bSAPATA\b',t): return 'SAPATAS','SAPATA'
    if re.search(r'\bGRID(?:\b|/)|\bP/?B\b|PARTE DE BAIXO',t):
        if re.search(r'\bFP|\bPAVER\b',t): return 'MOLDES_FP','GRID / PB'
        if re.search(r'\bFB|\bFMB|\bFC|\bMF',t): return 'MOLDES_FB','GRID / PB'
        return 'PENDENTE','FAMILIA A CONFIRMAR'
    nomes=[('CAV/SUP','CAVALETE SUPERIOR'),('PLUNGERS','PLUNGERS'),('HEAD PLUNGER','HEAD PLUNGER'),('HEAD PLNGR','HEAD PLUNGER'),
           ('HD SP/MANIFOLD','HD SP/MANIFOLD'),('HEAD SPACER/MANIFOLD','HEAD SPACER/MANIFOLD'),
           ('RESIST FUND','RESIST FUND'),('RTD ASSY','RTD ASSY'),('INSULATING SPAC','INSULATING SPAC'),
           ('GROMMET','GROMMET'),('SCRAPE OFF','RASPADOR'),('SCRAPE OF PLT','RASPADOR'),('SO PLT','RASPADOR'),
           ('AGITADOR','AGITADOR'),('AGITATOR','AGITADOR'),('RASPADOR','RASPADOR'),('HEATER','SISTEMA DE AQUECIMENTO'),
           ('SIST.AQUEC','SISTEMA DE AQUECIMENTO'),('SIST. AQUEC','SISTEMA DE AQUECIMENTO'),('HEAD LEG','HEAD LEG'),('SUPPORT RAIL','SUPPORT RAIL'),
           ('PINO_FIX','PINO_FIX'),('CORE PLUNGER','CORE PLUNGER'),('CONJUNTO FIXA','CONJUNTO DE FIXACAO'),('FIBRA DE VIDRO','FIBRA DE VIDRO')]
    for token,nome in nomes:
        if token in t:return 'AUXILIAR',nome
    if faturado and re.search(r'\b(?:COMPLETA|COMPLET|COMPLETO|COMPL)\b',t):
        return 'COMPLETOS','MOLDE COMPLETO'
    # Termos novos após as cavidades continuam pendentes de validação.
    if faturado and t.startswith('MOLD ') and re.search(r'\b\d+V(?:\s+[CSDF]/[FM](?:\s*\d+MM)?)*$',t):
        if re.search(r'\bFB|\bFMB|\bFC|\bMF',t):return 'MOLDES_FB','MOLDE FB'
        if re.search(r'\bFP|\bPAVER\b',t):return 'MOLDES_FP','MOLDE FP'
    return 'PENDENTE',descricao

def digest(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:24]

def normalizar(rows,limite):
    registros={}
    def data_linha(row):
        d=row['data_mes_grade'];return d.date() if isinstance(d,datetime) else d
    rows=[r for r in rows if date(2026,1,1)<=data_linha(r)<=limite and chave_texto(r['segmento']) in ('MOLDE','MOLDES')]
    grupos_com_produto={(data_linha(r).strftime('%Y-%m'),r['empresa_auditoria'],r['os_id']) for r in rows if str(r.get('produto_proprio') or '').strip()}
    for row in rows:
        d=row['data_mes_grade']; d=d.date() if isinstance(d,datetime) else d
        if not date(2026,1,1)<=d<=limite:continue
        if chave_texto(row['segmento']) not in ('MOLDE','MOLDES'):continue
        mes=d.strftime('%Y-%m')
        proprio=bool(str(row.get('produto_proprio') or '').strip())
        if not proprio and (mes,row['empresa_auditoria'],row['os_id']) in grupos_com_produto:continue
        if proprio:
            guid=row['id_linha_produto']
            if not guid:raise ValueError('Linha do produto sem identificador; revisar grade')
            key=(mes,row['empresa_auditoria'],'proprio',row['os_id'],guid)
            descricao=str(row['produto_proprio']);qtd=row['qtde_utilizada']
            codigo=row.get('id_cadastro_proprio') or row['cod_produto_proprio']
        else:
            guid=row.get('id_item_faturado')
            if guid is None:raise ValueError('Item faturado sem identificador; revisar grade')
            key=(mes,row['empresa_auditoria'],'faturado',row.get('tipo_item_faturado'),guid)
            descricao=str(row.get('descricao_conjunto') or '').strip()
            if not descricao:raise ValueError('Item faturado sem descricao')
            qtd=row.get('quantidade_faturada');codigo=row.get('codigo_item_faturado') or descricao
        categoria,componente=classificar(descricao, faturado=not proprio)
        qtd=float(qtd) if qtd is not None else None
        if qtd is not None:
            import math
            if not math.isfinite(qtd) or qtd<0:raise ValueError('Quantidade invalida na grade')
        nome=str(row.get('descricao_conjunto') or '').strip()
        completo=bool(re.search(r'\b(?:COMPLETA|COMPLET|COMPLETO|COMPL)\b',chave_texto(nome)))
        record=dict(mes_ref=mes,descricao=descricao,codigo_produto=str(codigo or ''),
                    quantidade=qtd,unidade=str(row['unidade'] or ''),categoria=categoria,componente=componente,
                    id_produto=digest(key),conjunto_id=digest((mes,row['empresa_auditoria'],row['os_id'])) if completo else '',
                    conjunto_nome=nome if completo else '',origem_quantidade='produto_proprio' if proprio else 'item_faturado')
        if key in registros:
            anterior=registros[key]
            if anterior['quantidade']!=qtd:raise ValueError('Quantidade conflitante na repeticao de produto')
            if completo and not anterior['conjunto_id']:registros[key]=record
            continue
        registros[key]=record
    return {'disponivel':bool(registros),'formato':'pivot_categorias','registros':list(registros.values()),
            'inicio':'2026-01-01','fim':limite.isoformat(),'data_base':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
            'avisos':['Mes definido pela data da grade CPS. Produto proprio tem prioridade; na ausencia, descricao e quantidade do item faturado.',
                      'Mes atual parcial. Repeticoes da mesma linha de produto sao contadas uma vez por mes.',
                      'Moldes completos utilizam o volume de GRID/PB da composicao, sem somar novamente seus componentes.']}

def ler_producao_cps():
    import psycopg
    password=os.getenv('DB_PASSWORD')
    if not password:
        from credencial_cps import ler_senha
        password=ler_senha()
    limite=min(hoje(),date(2026,12,31))
    if limite<date(2026,1,1):return normalizar([],limite)
    conn=None
    for host in [os.getenv('DB_HOST','columbia.sytes.net'),'10.250.100.251']:
        try:
            conn=psycopg.connect(host=host,port=5432,dbname='CPS',user='DevLeitura',password=password,connect_timeout=6,
                options='-c default_transaction_read_only=on -c statement_timeout=30000')
            break
        except psycopg.OperationalError:continue
    if conn is None:raise RuntimeError('CPS indisponivel; ultima publicacao preservada')
    with conn:
        with conn.cursor() as cur:
            cur.execute(montar_sql(limite));cols=[d.name for d in cur.description];rows=[dict(zip(cols,r)) for r in cur.fetchall()]
    if len(rows)>=20001:raise ValueError('Consulta atingiu limite; particionar antes de publicar')
    return normalizar(rows,limite)
