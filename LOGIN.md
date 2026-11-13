# Entrada por identificação local

Implementação simplificada conforme solicitado: **sem backend, banco de dados,
cadastro de usuários ou serviço de autenticação**. Funciona na hospedagem estática
atual, inclusive no GitHub Pages. Não há novas dependências.

## Como usar

1. Abra o endereço do dashboard. Sem uma identificação válida neste navegador,
   a interface abre `login.html`.
2. Informe um e-mail válido com domínio exato **@colmac.com** e clique em **Entrar**.
   Nomes sem e-mail, outros domínios e subdomínios não são aceitos. Letras maiúsculas
   e espaços antes/depois são normalizados. Identificações antigas sem esse domínio
   voltam à tela de entrada.
3. O navegador registra usuário, data e hora e abre o dashboard original.
4. **Sair** remove a identificação, mas preserva os registros anteriores.

O formulário segue o ZIP fornecido: fundo vermelho `#BE1523`, grade industrial,
logotipo Red Molds, cartão branco centralizado e fontes Barlow/Barlow Condensed.
A senha foi omitida porque não existe nem será criado um serviço para validá-la.
Nenhuma senha é solicitada, transmitida ou armazenada.

## Identificação e persistência

- Sem **Manter conectado**, a identificação fica no `sessionStorage`, durante a
  sessão da aba/janela, com limite de oito horas. Alguns navegadores restauram
  sessões ao reabrir abas.
- Com a opção ativada, fica no `localStorage`, por até 30 dias.
- Esses prazos são conveniência de navegação, não validade de autenticação.
- Dados inválidos ou expirados levam novamente à entrada.
- Se o navegador bloquear toda forma de armazenamento, é necessário permitir
  o armazenamento do site para continuar. Não há entrada por fragmento de URL.

## Registro dos acessos

São mantidas até 100 entradas no `localStorage`, na chave
`dashboard-acessos-v1`, com somente `usuario`, `data` e `hora`.
As datas e horas são as do dispositivo de quem acessou.

Os registros são locais ao navegador, perfil e endereço do site. Não são enviados
ao GitHub, Excel ou servidor e não podem ser consultados centralmente em outros
dispositivos. Limpar os dados do site apaga os registros. Falhas de armazenamento
do histórico não impedem abrir o dashboard.

Para consultar os registros no próprio navegador, abra as ferramentas do
desenvolvedor → Application/Aplicativo → Local Storage → endereço do dashboard
→ `dashboard-acessos-v1`.

## Limites desta solução

**É uma tela de identificação, não autenticação nem proteção de dados.** O e-mail é
autodeclarado: a validação confere formato e domínio, sem verificar a existência
da caixa postal ou sua titularidade. O armazenamento pode
ser editado e o fluxo pode ser contornado. Os arquivos do dashboard e `dados.json`
continuam públicos na hospedagem atual. Repositório e histórico públicos também
continuam acessíveis. O redirecionamento da interface não muda isso.

Para validar credenciais ou restringir os arquivos de verdade, seria necessário
um serviço de autenticação e controle de acesso na hospedagem. Isso não foi
implementado, por solicitação de manter apenas a identificação simples.

## Arquivos para publicação

Enviar os arquivos alterados `index.html` e `app.js`, os novos `login.html`,
`login.css`, `acesso.js`, `acesso.css`, `img/login-grid.svg` e `img/login-logo.png`.
Manter os demais arquivos existentes. `LOGIN.md` documenta o funcionamento.
Não executar `support.js` nem importar o React do ZIP: são apenas o runtime da
referência visual, desnecessários nesta implementação.
