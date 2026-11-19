# Produção - KPI

Produção vem da grade CPS **ITENS PRODUZIDO (COM DEPENDENCIAS)**, segmento MOLDE,
produto próprio e `qtde_utilizada`. A consulta original está em
`consultas/producao_pivot_base.sql`. Somente SELECT, transação read-only, timeout
e limite de linhas. Somente entram itens concluídos e faturados no mesmo mês.
Exige `concluido=1`, data de conclusão preenchida até hoje e OS não cancelada.
Quando o produto próprio possui uma OS de fabricação vinculada, a conclusão
é verificada nessa OS; sem vínculo, utiliza a OS principal. A conclusão da
montagem não substitui a conclusão de uma OS de fabricação vinculada e aberta.
Conclusão e faturamento em meses diferentes ficam fora deste indicador,
inclusive do acumulado; não são transferidos para outro mês.
A saída não contém números de NF. Por solicitação do usuário, os detalhes dos
produtos incluem cliente e número da OS da grade. O total do produto permanece
consolidado, com o volume discriminado por cliente/OS/mês logo abaixo.

Quando o produto próprio está vazio na grade, usar descrição e quantidade do item
faturado. Produto próprio preenchido tem prioridade na mesma OS/mês; não somar
o item faturado à sua composição. Repetições das junções são eliminadas pelo GUID
da linha própria ou identificador do item faturado, conforme a origem. Itens
fiscais distintos são preservados. Quantidades conflitantes na mesma chave
impedem a publicação. A origem da quantidade é registrada na base gerada.

O início é 01/01/2026. O fim é hoje em America/Sao_Paulo, limitado a 31/12/2026.
O dia atual é incluído e datas futuras são excluídas. O mês atual é parcial
e inicialmente selecionado; o filtro permite o acumulado de janeiro até hoje.

## Cartões

- **Moldes Completos**: conjuntos identificados como COMPLETO/COMPLET/COMPLETA/COMPL.
  Exige conclusão da OS principal no mesmo mês do faturamento. Possui registro
  de volume próprio, sem depender de o componente ter sido fabricado naquele
  mês: um conjunto pode ser montado com componentes concluídos anteriormente.
  Volume pelo GRID/PB da composição, sem somar os demais componentes. Quando toda
  a composição está ausente, usar o volume explícito do item completo faturado.
  Se nenhum desses volumes estiver informado, permanece pendente.
- **Moldes FP**: GRID/PB de FP ou PAVER.
- **Moldes FB**: GRID/PB de FB (FBE/FBV/FBEDESM etc.), FMB, FC ou MF.
- Molde avulso com família FP/FB e assinatura dimensional reconhecida também
  entra na família, mesmo sem GRID/PB. Termos novos continuam pendentes.
- **Sapatas**: SPT/SHOE/SAPATA, inclusive dentro dos completos.
- **Castelos**: CAST/CAST. C/PORT.SP/CASTELO. Cavalete não acrescenta castelo.
- **Canecos**: ENDCORE/COREBAR/CANECO, conforme nomenclaturas confirmadas.

São seis cartões clicáveis. As categorias se sobrepõem: GRID de conjunto completo alimenta Completos e FP/FB.
Não somar os cartões como um total de peças. O clique abre itens e volumes abaixo.
Em Completos, cada modelo expande sua composição. Não há informações de NF na tela,
rankings ou tabelas de recorrência. Nomenclaturas não reconhecidas ficam pendentes.

O painel mensal segue a Opção 1 aprovada: seis minigráficos em uma grade de três
colunas (duas no tablet, uma no celular), uma categoria por quadro. Cada gráfico
tem escala independente explícita, valores sobre as barras e total no período.
O mês atual é identificado como parcial e sua barra usa uma tonalidade mais clara.
Os filtros existentes atualizam simultaneamente os cartões e os seis gráficos.

Cada linha de produto é contada uma vez por mês (empresa/OS/GUID), removendo
multiplicações das junções. A reaparição em outro mês não passa na regra de
conclusão no mesmo mês. Campos vazios não viram zeros. A data de conclusão e
a OS efetiva da produção acompanham cada registro para conferência.

## Atualização

A elegibilidade fiscal é aplicada em `consultas/producao_documentos_validos.sql`:
notas canceladas são excluídas; NF-e dos modelos 55/65 exige status 100.
Devoluções não entram como produção. Quando a devolução válida referencia
explicitamente a nota de origem e o mesmo produto, seu volume é abatido da
origem, inclusive em mês anterior. Uma devolução integral retira o item;
uma parcial mantém o saldo e aplica a mesma proporção à composição.
Referências duplicadas não multiplicam o desconto. Várias origens possíveis
para o mesmo item devolvido não são atribuídas automaticamente. Uma nova nota
válida continua elegível; não se elimina um item apenas pela repetição da OS.
As devoluções consideradas têm emissão até a data atual da consulta.

Teste SQL com dados sintéticos, sem gravar no CPS:
`$env:CPS_TEST_INTEGRACAO='1'; py -3.12 -m unittest discover -s tests -p "test_documentos_validos.py"`.

O publicador mantém melhorias/faturamento/qualidade da planilha e consulta
`producao_pivot.py` para produção. Não escreve no Excel. A tarefa Windows verifica
a cada minuto; republica após salvamento do Excel ou a cada nova janela de cinco
minutos para o CPS. O navegador consulta o JSON a cada minuto. GitHub Pages pode
acrescentar tempo. Em falha de leitura, a publicação anterior é preservada.

A senha vem de DB_PASSWORD ou do Cofre de Credenciais do Windows do usuário
central, alvo `DashboardGerencial/CPS/DevLeitura`. Não há senha em arquivos do
projeto. Outra máquina/usuário precisa configurar sua credencial. Requer psycopg.

Publicação recorrente autorizada expressamente pelo usuário em 19/11/2026 para
`Glbonfim-Dev/Dashboard-Gerencial-PCP` e o site publicado. A configuração
`CPS_PUBLICACAO_AUTORIZADA=True` habilita os ciclos sem confirmação por salvamento.
`--no-upload` continua disponível para conferir a leitura apenas localmente.

`dados.json` é gerado: em conflito de Git, regenerar, nunca misturar por merge
textual. `saida/` guarda auditorias locais e é ignorada pelo Git. Mudanças da
consulta-base exigem revisão da semântica da grade.

Na publicação automática, o arquivo de trabalho é `automation/dados_runtime.json`,
ignorado pelo Git. O publicador envia seu conteúdo para `dados.json` no destino
configurado, sem exigir commit manual local. `--no-upload` gera o `dados.json`
local para conferência. A autorização de publicação, quando concedida, vale para
os ciclos recorrentes; não existe pergunta interativa por salvamento.

Testes: `py -3.12 -m unittest discover -s tests -p "test_*.py"`,
`node tests/test_producao.cjs`, `node tests/test_acesso.cjs`.
