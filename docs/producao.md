# Produção - KPI

O dashboard lê exclusivamente a aba **Produção - KPI** de
**Melhorias - Faturamento moldes 2026.xlsx**, junto às leituras de ações,
faturamento e qualidade já realizadas por `publicar_dashboard.py`.
Somente registros de **2026** entram no painel.

## Fonte e atualização

### Preenchimento manual atual

`descricao_nf` identifica o conjunto comercial. Cada molde completo é agrupado
por NF + OS principal + descrição fiscal; suas linhas repetidas não viram vários
moldes. `produto_proprio` identifica os componentes que ficam dentro desse grupo
(`COMPONENTE_DE_MOLDE`). Itens de outras OS da mesma NF ficam fora do grupo,
como `COMPONENTE_AVULSO`, outro `MOLDE_COMPLETO` ou `OUTROS`, conforme a descrição
fiscal. A ausência de OS usa NF + descrição e é registrada no método de vínculo.
Moldes inteiros com descrição MOLD + produto reconhecido, sem componente no nome,
seguem a regra de molde completo; isso não comprova composição física igual a KIT.

O painel permite selecionar NF e molde completo. A seção de composição mostra
somente os componentes do conjunto selecionado, em cartões por tipo. Não recria
rankings nem tabelas de recorrência. Exemplo: NF 10921, OS 6984, contém 1 GRADE,
15 SAPATAS e outros oito tipos; agitador/raspador de outras OS não entram nele.

No layout aprovado, cada conjunto possui seu próprio cartão com descrição fiscal,
NF, OS principal e indicador **1 conjunto identificado**. Os cartões dos componentes
ficam dentro desse cartão pai. Ao selecionar um molde, a visão geral e o gráfico
mensal dão lugar ao detalhe, acompanhado da seção **Fora deste molde · mesma NF**.
Essa seção inclui outros conjuntos e itens de outras OS da nota, sem somar
quantidades de componentes como se fossem unidades do conjunto.

Sem seleção de NF/molde, o painel mantém os indicadores e a evolução mensal.
Ao selecionar uma NF, o seletor de moldes mostra somente conjuntos dessa nota
e do período escolhido. Os filtros são preservados na atualização automática
quando seus valores ainda existem na base.

Campos de produto próprio vazios preservam a linha fiscal para classificação,
sem inventar a estrutura. Quantidades vazias são `null`; subtotais conhecidos
são acompanhados de aviso de registros sem quantidade. A contagem de moldes
é de grupos comerciais identificados, não de unidades fiscais não informadas.

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

O cartão **Moldes completos** conta os grupos NF + OS + descrição fiscal.
Não infere quantidades fiscais dos conjuntos a
partir de suas estruturas. O cartão **Castelos na estrutura** inclui os castelos
informados como produtos próprios, inclusive os vinculados a conjuntos completos.

Após salvar o Excel, a tarefa Windows existente verifica alterações a cada minuto,
aguarda o arquivo estabilizar e executa `publicar_dashboard.py`. O site consulta
o JSON a cada minuto e atualiza cartões e gráficos mantendo os filtros.
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

Filtros por ano, mês e componente; cartões de moldes completos, castelos,
grades e sapatas; evolução mensal em largura completa. Meses parciais são identificados pela fonte.

A matriz mensal não identifica modelos, notas ou CFOP. Por isso o painel
apresenta quantidades por componente e não oferece filtro de operação nesse
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
