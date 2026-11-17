# Produção - KPI

O dashboard lê exclusivamente a aba **Produção - KPI** de
**Melhorias - Faturamento moldes 2026.xlsx**, junto às leituras de ações,
faturamento e qualidade já realizadas por `publicar_dashboard.py`.
Somente registros de **2026** entram no painel.

## Fonte e atualização

O formato atual da aba é uma matriz: `mes_ref` na primeira coluna, tipos de
componente nas demais colunas e `periodo_parcial` indicando `S` ou `N`.
Exemplo:

| mes_ref | CASTELO | GRADE | MOLDE COMPLETO | SAPATA | periodo_parcial |
|---|---:|---:|---:|---:|---|
| 2026-10 | 1 | 13 | 18 | 283 | N |

`producao_reader.py` abre o arquivo **somente para leitura**. Não atualiza
nenhuma planilha, não consulta o ERP e não usa a planilha mensal histórica
como fonte alternativa. A gravação de informações na planilha principal
deve ocorrer **somente quando o usuário solicitar**. A automação existente
continua lendo os dados salvos e publicando o JSON para o dashboard.

A coluna sem título presente na matriz é exibida como **SEM CLASSIFICAÇÃO**
quando contém quantidades. Não se presume o tipo dessas peças.
Ausências não são convertidas em zeros. Meses e quantidades inválidos
interrompem a publicação, preservando o último JSON válido.

## Indicadores e limites

Filtros por ano, mês e componente; cartões de moldes completos, castelos,
grades e sapatas; evolução mensal, ranking de componentes, recorrência em
meses e exportação CSV da seleção. Meses parciais são identificados pela fonte.

A matriz mensal não identifica modelos, notas ou CFOP. Por isso o painel
apresenta ranking por componente e não oferece filtro de operação nesse
formato. Não se deve reconstituir esse detalhe por suposição.

O leitor também aceita uma tabela com `mes_ref`, `tipo_componente` e
`quantidade`. Descrição, chave do molde e CFOP são opcionais nesse formato.
O filtro de operação aparece apenas quando todos os registros têm CFOP.
Não misture totais mensais e itens fiscais na mesma tabela: isso duplicaria
as quantidades.

As quantidades são faturadas, não produção concluída. Castelos incorporados
a moldes completos não são contados separadamente. Eficiência, produtividade
e metas de fabricação não são inferidas desses números.

## Organização do repositório

- `producao_reader.py`: leitura e validação da fonte principal.
- `producao.js`: filtros, cálculos e gráficos da nova aba.
- `index.html`, `style.css`, `app.js`: integração visual e navegação existentes.
- `dados.json`: dados publicados pelo site; conserva as demais áreas.
- `tests/test_producao.py` e `tests/test_producao.cjs`: testes de leitura e filtros.

Extrações SQL, relatórios exploratórios, planilhas derivadas e backups em
`saida/` são artefatos locais ignorados pelo Git. Não são dependências do
dashboard. Scripts pontuais que gravavam nas planilhas foram retirados
da automação do projeto.

## Verificação

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py"
node tests/test_producao.cjs
node tests/test_acesso.cjs
```
