# Dashboard Gerencial – Melhorias e Faturamento 2026

Automação Windows central que verifica o Excel compartilhado a cada minuto,
calcula os indicadores quando detecta um novo salvamento, cria `dados.json` e o
publica no GitHub pela API REST. O GitHub Pages consome esse JSON e atualiza o
dashboard sem depender do computador de quem editou a planilha.

## Estrutura

```text
publicar_dashboard.py  fluxo principal, validação e lock
monitorar_excel.py      detector de alterações no Excel compartilhado
automation/             instalação e remoção da tarefa do Windows
config.py               abas, colunas, metas e tempos de espera
excel_reader.py         leitura, normalização e indicadores
github_client.py        criação/atualização via API REST
logger.py               log rotativo
ThisWorkbook.vba        evento VBA desativado; automação não depende de macro
index.html              dashboard
style.css               layout corporativo e responsivo
app.js                  filtros, gráficos e tabelas
dados.json              dados gerados (após a primeira execução)
tests/                   testes automatizados
logs/dashboard.log      histórico local de execução
```

## 1. Preparar o Python

No PowerShell, dentro da pasta do projeto:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe" -3 -m pip install -r requirements.txt
```

O projeto foi configurado para o Python Launcher localizado em:

```text
C:\Users\guilherme.bonfim\AppData\Local\Programs\Python\Launcher\py.exe
```

## 2. Configurar a planilha

O mapeamento atual, confirmado na planilha real, está em `config.py`:

| Informação | Aba | Coluna/linhas |
|---|---|---|
| Ação | AÇÕES DE MELHORIA | F, a partir da linha 8 |
| Responsável | AÇÕES DE MELHORIA | G |
| Prazo | AÇÕES DE MELHORIA | H |
| Status | AÇÕES DE MELHORIA | J |
| Mês | FATURAMENTO MOLDES 2026 | D15:D26 |
| Realizado | FATURAMENTO MOLDES 2026 | H15:H26 |

A planilha atual não possui colunas de observação, data de conclusão ou meta.
Essas colunas estão configuradas como opcionais. Quando forem adicionadas,
preencha `coluna_observacao`, `coluna_data_conclusao` e `coluna_meta`.

Enquanto não houver uma coluna de meta, os valores oficiais ficam no dicionário
`metas_mensais` de `config.py`. Para 2026, a meta é de R$ 1.000.000 por mês de
janeiro a outubro e R$ 1.200.000 em novembro e dezembro, totalizando
R$ 12.400.000 no ano.

O quadro “Meta x Realizado” compara a meta configurada para o mês corrente com
o realizado desse mês. O gráfico mensal continua exibindo o ano completo.
Ao clicar em qualquer ponto do gráfico mensal, o quadro passa a comparar a meta,
o realizado e o atingimento do mês selecionado.

No gráfico “Ações por Responsável”, clicar em uma barra ou no nome da pessoa abre
o detalhamento completo das ações dela, com resumo por status.

O painel lateral de filtros fica recolhido por padrão. A seta na lateral abre ou
fecha o painel, e o navegador memoriza a última escolha do usuário.

Ao clicar em uma fatia ou legenda do gráfico de status, o modal mostra as ações
daquele status. Com “Responsável = Todos”, inclui todas as pessoas; quando um
responsável está selecionado, mostra somente as ações dele.

## 3. Testar localmente sem GitHub

### Aba Qualidade KPI 2026

O dashboard possui duas abas de navegação: **Melhorias e Faturamento** e
**Qualidade KPI 2026**, com o mesmo cabeçalho, cartões, painéis e filtros laterais.
A aba de qualidade já existe no Excel compartilhado; não é necessário criá-la
ou instalar macros. O nome fica em `QUALIDADE_CONFIG` de `config.py`.

O Python identifica as tabelas da qualidade pelo cabeçalho **Mês** e pelos nomes
dos indicadores. Inserções de linhas e deslocamentos de colunas são aceitos
enquanto os cabeçalhos forem mantidos. Novas colunas à direita de **Mês** entram
no detalhamento; novas áreas/máquinas entram também nos gráficos respectivos.
Novos blocos com cabeçalho **Mês**, campos e datas aparecem no seletor de
detalhamento. Renomear os cabeçalhos que identificam os indicadores ou mudar o
formato das tabelas exige revisar o reconhecimento em `ler_qualidade`.

São lidos RNC total, cliente, fornecedor, interna, áreas, máquinas, horas gastas,
custos da qualidade, custos por categoria e horas/custos por máquina. Os dados
ficam no campo adicional `qualidade` de `dados.json`; os campos anteriores são
preservados. O painel antigo também funciona com JSON sem esse novo campo.

Os filtros de ano e mês da qualidade são independentes dos filtros de ações.
As tabelas históricas de 2025 ficam separadas das de 2026 pelo filtro de ano.
Painéis de indicadores removidos da planilha são ocultados automaticamente.
Campos vazios e erros de fórmula
(por exemplo `#DIV/0!`) aparecem como **Sem dados**, sem gerar zeros artificiais;
zeros preenchidos são mantidos. Os erros encontrados ficam nas observações da
aba. Durações acima de 24 horas são preservadas. Percentuais e limites de meta
não são somados. Os totais são calculados com os meses preenchidos de cada
bloco, sem forçar conciliação entre tabelas distintas da planilha.

A tarefa existente detecta o salvamento de qualquer aba do arquivo a cada
minuto, aguarda sua estabilidade e publica todos os indicadores no mesmo JSON.
O navegador consulta o JSON a cada minuto e mantém a aba e os filtros ativos.
A atualização depende também do tempo de publicação do GitHub Pages; não é
instantânea. O Excel precisa recalcular e salvar os resultados das fórmulas.

Para disponibilizar a nova interface, envie `index.html`, `app.js`, `style.css`
e o JSON atualizado ao repositório existente. Mantenha `config.py`,
`excel_reader.py` e `publicar_dashboard.py` atualizados no computador da
automação. Para testar sem publicação use `--no-upload`, conforme abaixo.

Ao publicar mudanças na interface, atualize também o parâmetro `v` dos links
de `style.css` e `app.js` em `index.html`, mantendo a mesma versão nos dois.
Isso impede que o navegador reutilize CSS/JavaScript de uma versão anterior
com o HTML novo. Publique os três arquivos juntos. O GitHub Pages pode levar
alguns minutos para disponibilizar a nova publicação.

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe" -3 .\publicar_dashboard.py "Z:\PUBLICO\PCP\CONTROLE GRID - PRAZOS\EDEMIR\Melhorias - Faturamento moldes 2026.xlsm" --no-upload
```

Resultado esperado:

- código de saída `0`;
- `dados.json` criado em UTF-8;
- números gravados como números JSON;
- apenas o nome do Excel em `arquivo_origem`;
- nenhuma credencial ou caminho da rede no JSON;
- `logs/dashboard.log` com todas as etapas;
- `dashboard.lock` removido ao final.

## 4. Configurar a publicação no GitHub

1. Copie `.env.example` para `.env`.
2. Crie um token do GitHub com permissão mínima de escrita no conteúdo do
   repositório escolhido.
3. Preencha o `.env`:

```dotenv
GITHUB_TOKEN=seu_token
GITHUB_OWNER=nome_do_proprietario
GITHUB_REPO=nome_do_repositorio
GITHUB_BRANCH=main
GITHUB_JSON_PATH=dados.json
```

O `.env` está no `.gitignore`. O token nunca é escrito no log ou no JSON.

Para publicar `dados.json` na raiz de outra pasta do repositório, use, por
exemplo, `GITHUB_JSON_PATH=docs/dados.json`. O frontend deve estar nessa mesma
pasta, pois usa `fetch("./dados.json")`.

Teste de publicação:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe" -3 .\publicar_dashboard.py "\\srvdc01\dados\PUBLICO\PCP\CONTROLE GRID - PRAZOS\EDEMIR\Melhorias - Faturamento moldes 2026.xlsx"
```

O cliente consulta o SHA atual, cria ou atualiza o arquivo e usa a mensagem:

```text
Atualização automática dashboard - DD/MM/AAAA HH:MM
```

Falhas temporárias de conexão, HTTP 429 ou HTTP 5xx geram até três tentativas,
com esperas de 5 e 10 segundos.

## 5. Instalar a automação central

No PowerShell, dentro da pasta do projeto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\automation\instalar_tarefa.ps1
```

A tarefa `Dashboard Gerencial - Atualizar Site` roda a cada minuto enquanto o
usuário deste computador estiver conectado. Ela compara tamanho e data de
modificação do Excel com o último salvamento publicado, aguarda o arquivo ficar
estável e só então chama `publicar_dashboard.py`. Uma falha não grava o estado,
portanto a publicação é tentada novamente no minuto seguinte. A tarefa usa
`pythonw.exe`, então funciona silenciosamente, sem abrir janelas de terminal.

Para remover a tarefa:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\automation\remover_tarefa.ps1
```

O evento `Workbook_AfterSave` antigo deve ser removido do módulo
`EstaPastaDeTrabalho` da planilha. O arquivo `ThisWorkbook.vba` contém a versão
inativa para referência. Os usuários precisam apenas salvar o Excel na rede.

## 6. Visualizar o dashboard localmente

Navegadores bloqueiam `fetch` quando o HTML é aberto diretamente por
`file://`. Inicie um servidor local:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe" -3 -m http.server 8000
```

Abra `http://localhost:8000`. Os filtros de responsável, status e período
recalculam KPIs, gráficos e tabelas. “Ver todas as ações” abre o detalhamento.

## 7. Publicar no GitHub Pages

Envie para a pasta configurada do repositório:

- `index.html`;
- `style.css`;
- `app.js`;
- a pasta `img` com `images.png`;
- `dados.json`.

Nas configurações do repositório, habilite GitHub Pages para a branch e pasta
correspondentes. O Chart.js é carregado por CDN; o restante é estático. Enquanto
estiver aberta, a página consulta `dados.json` a cada minuto, preserva os filtros
selecionados e redesenha a tela quando encontra uma nova atualização.

## 8. Testes e diagnóstico

Executar testes:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe" -3 -m unittest discover -s tests -v
```

Saídas do programa:

- `0`: sucesso;
- `1`: erro de leitura, JSON ou GitHub;
- `2`: caminho ausente/inválido;
- `3`: outra execução já está ativa.

O log usa UTF-8, rotação em 2 MB e cinco backups. Para preservar os acentos no
Windows PowerShell antigo, abra o arquivo no VS Code ou use:

```powershell
Get-Content .\logs\dashboard.log -Encoding UTF8 -Tail 30
```
