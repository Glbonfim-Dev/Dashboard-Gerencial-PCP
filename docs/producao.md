# Produção - KPI

O dashboard lê exclusivamente a aba **Produção - KPI** de
**Melhorias - Faturamento moldes 2026.xlsx**, junto às leituras de ações,
faturamento e qualidade já realizadas por `publicar_dashboard.py`.
Somente registros de **2026** entram no painel.

## Fonte e atualização

### Preenchimento manual atual

O usuário localiza, valida e insere os dados manualmente. O formato atual usa
`nota_fiscal`, `emissao_nf`, `descricao_nf`, `os_principal`, `cod_produto_proprio`,
`produto_proprio`, `qtde_utilizada`, `os_fabricacao` e campos de materiais de
fabricação. As quantidades do painel vêm de `qtde_utilizada`, por produto próprio;
`qtde_utilizada_fabricacao` não é somada aos componentes.

Somente linhas de emissão de 2026 entram. Produto repetido apenas por materiais
distintos é contado uma vez quando seus demais dados são idênticos. Utilizações
sem materiais são preservadas por linha, assim como notas distintas. A classificação
de componente usa a descrição do produto próprio (CAST/CASTELO, GRID/P/B, SHOE/SPT,
etc.); descrições sem correspondência permanecem em OUTROS COMPONENTES.

O cartão **OS de moldes completos** conta OS principais distintas com descrição
fiscal explicitamente completa. Não infere quantidades fiscais dos conjuntos a
partir de suas estruturas. O cartão **Castelos na estrutura** inclui os castelos
informados como produtos próprios, inclusive os vinculados a conjuntos completos.

Após salvar o Excel, a tarefa Windows existente verifica alterações a cada minuto,
aguarda o arquivo estabilizar e executa `publicar_dashboard.py`. O site consulta
o JSON a cada minuto e atualiza cartões, gráficos e tabelas mantendo os filtros.
O computador da automação deve estar ligado, com sessão ativa e acesso à rede e
ao GitHub. Fórmulas precisam estar calculadas e salvas no Excel. A publicação do
GitHub Pages também pode acrescentar tempo ao ciclo.

### Formatos anteriores compatíveis

O leitor também aceita a matriz: `mes_ref` na primeira coluna, tipos de
componente nas demais colunas e `periodo_parcial` indicando `S` ou `N`.
Exemplo:

| mes_ref | CASTELO | GRADE | MOLDE COMPLETO | SAPATA | periodo_parcial |
|---|---:|---:|---:|---:|---|
| 2026-10 | 1 | 13 | 18 | 283 | N |

`producao_reader.py` abre o arquivo **somente para leitura**. Não atualiza
nenhuma planilha, não consulta o ERP e não usa a planilha mensal histórica
como fonte alternativa. O preenchimento da planilha principal é feito
**manualmente pelo usuário**. A automação existente
continua lendo os dados salvos e publicando o JSON para o dashboard.

A coluna sem título presente na matriz é exibida como **SEM CLASSIFICAÇÃO**
quando contém quantidades. Não se presume o tipo dessas peças.
Ausências não são convertidas em zeros. Meses e quantidades inválidos
interrompem a publicação, preservando o último JSON válido.

## Indicadores e limites

A tabela de recorrência tem filtros próprios por texto do item, componente,
intervalo de quantidade, intervalo de meses ativos e entrega futura (incluindo
não discriminado). Eles atuam sobre os totais do período escolhido nos filtros
gerais. O CSV respeita também essa seleção da tabela. O botão de limpeza da
tabela preserva os filtros gerais e os gráficos.

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

No formato de estrutura, as quantidades representam componentes utilizados
nas OS vinculadas às notas, incluindo castelos incorporados quando informados.
Nos formatos mensais anteriores, os números são os totais já consolidados na
fonte. Nenhum formato comprova a produção concluída. Eficiência, produtividade
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
