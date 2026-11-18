# Produção - KPI

Produção vem da grade CPS **ITENS PRODUZIDO (COM DEPENDENCIAS)**, segmento MOLDE,
produto próprio e `qtde_utilizada`. A consulta original está em
`consultas/producao_pivot_base.sql`. Somente SELECT, transação read-only, timeout
e limite de linhas. O mês acompanha a data da grade, conforme aprovado.
A saída não contém números de NF, OS nem clientes.

O início é 01/01/2026. O fim é hoje em America/Sao_Paulo, limitado a 31/12/2026.
O dia atual é incluído e datas futuras são excluídas. O mês atual é parcial
e inicialmente selecionado; o filtro permite o acumulado de janeiro até hoje.

## Cartões

- **Moldes Completos**: conjuntos identificados como COMPLETO/COMPLET/COMPLETA/COMPL.
  Volume pelo GRID/PB da composição, sem somar os demais componentes. Sem GRID/PB,
  o volume permanece pendente.
- **Moldes FP**: GRID/PB de FP ou PAVER.
- **Moldes FB**: GRID/PB de FB (FBE/FBV/FBEDESM etc.), FC ou MF.
- **Sapatas**: SPT/SHOE/SAPATA, inclusive dentro dos completos.
- **Castelos**: CAST/CAST. C/PORT.SP/CASTELO. Cavalete não acrescenta castelo.

As categorias se sobrepõem: GRID de conjunto completo alimenta Completos e FP/FB.
Não somar os cartões como um total de peças. O clique abre itens e volumes abaixo.
Em Completos, cada modelo expande sua composição. Não há informações de NF na tela,
rankings ou tabelas de recorrência. Nomenclaturas não reconhecidas ficam pendentes.

Cada linha de produto é contada uma vez por mês (empresa/OS/GUID), removendo
multiplicações das junções. A reaparição em outro mês é preservada conforme a
grade, sem comprovar nova produção física. Campos vazios não viram zeros.

## Atualização

O publicador mantém melhorias/faturamento/qualidade da planilha e consulta
`producao_pivot.py` para produção. Não escreve no Excel. A tarefa Windows verifica
a cada minuto; republica após salvamento do Excel ou a cada nova janela de cinco
minutos para o CPS. O navegador consulta o JSON a cada minuto. GitHub Pages pode
acrescentar tempo. Em falha de leitura, a publicação anterior é preservada.

A senha vem de DB_PASSWORD ou do Cofre de Credenciais do Windows do usuário
central, alvo `DashboardGerencial/CPS/DevLeitura`. Não há senha em arquivos do
projeto. Outra máquina/usuário precisa configurar sua credencial. Requer psycopg.

Estado da implantação: código e base validados localmente. A revisão automática
bloqueou o envio dos novos dados de produção ao GitHub. Por isso,
`CPS_PUBLICACAO_AUTORIZADA=False` em config.py impede também o upload indireto
pela tarefa existente até autorização expressa do usuário. `--no-upload` continua
permitindo validar a leitura local. Nenhum envio alternativo deve contornar esse bloqueio.

`dados.json` é gerado: em conflito de Git, regenerar, nunca misturar por merge
textual. `saida/` guarda auditorias locais e é ignorada pelo Git. Mudanças da
consulta-base exigem revisão da semântica da grade.

Testes: `py -3.12 -m unittest discover -s tests -p "test_*.py"`,
`node tests/test_producao.cjs`, `node tests/test_acesso.cjs`.
