"use strict";

// Identificação local, por solicitação do projeto. Não autentica credenciais
// nem protege arquivos públicos. Nunca solicita ou armazena senhas.
(() => {
  const ENTRY_KEY = "dashboard-identificacao-v1";
  const LOG_KEY = "dashboard-acessos-v1";
  const MAX_RECORDS = 100;
  const SESSION_MS = 8 * 60 * 60 * 1000;
  const REMEMBER_MS = 30 * 24 * 60 * 60 * 1000;
  const form = document.querySelector("#login-form");
  const destination = (file) => new URL(file, document.baseURI).href;
  const stores = () => ["localStorage", "sessionStorage"];

  function limparIdentificacao() {
    stores().forEach((name) => {
      try { window[name].removeItem(ENTRY_KEY); } catch (_) { /* Navegador pode bloquear armazenamento. */ }
    });
  }

  function restaurarIdentificacao() {
    for (const name of stores()) {
      try {
        const saved = JSON.parse(window[name].getItem(ENTRY_KEY) || "null");
        if (saved && typeof saved.usuario === "string" && saved.usuario.trim().length >= 2 &&
            typeof saved.expiraEm === "number" && saved.expiraEm > Date.now()) return saved;
        window[name].removeItem(ENTRY_KEY);
      } catch (_) { /* Registro ausente, inválido ou armazenamento bloqueado. */ }
    }
    return null;
  }

  function salvarIdentificacao(usuario, remember) {
    limparIdentificacao();
    const entry = JSON.stringify({ usuario, expiraEm: Date.now() + (remember ? REMEMBER_MS : SESSION_MS) });
    // Se armazenamento persistente estiver indisponível, usa a sessão da aba.
    for (const name of remember ? stores() : ["sessionStorage"]) {
      try { window[name].setItem(ENTRY_KEY, entry); return true; } catch (_) { /* Tenta a próxima opção. */ }
    }
    return false;
  }

  function registrarAcesso(usuario) {
    try {
      let records;
      try { records = JSON.parse(localStorage.getItem(LOG_KEY) || "[]"); } catch (_) { records = []; }
      if (!Array.isArray(records)) records = [];
      const now = new Date();
      records.push({ usuario, data: now.toLocaleDateString("pt-BR"), hora: now.toLocaleTimeString("pt-BR", { hour12: false }) });
      localStorage.setItem(LOG_KEY, JSON.stringify(records.slice(-MAX_RECORDS)));
    } catch (_) { /* Falha no registro local nunca impede abrir o dashboard. */ }
  }

  if (form) {
    if (restaurarIdentificacao()) {
      window.location.replace(destination("index.html"));
      return;
    }
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.querySelector("#usuario");
      const usuario = input.value.trim();
      const error = document.querySelector("#login-error");
      if (usuario.length < 2 || usuario.length > 100 || /[\u0000-\u001f]/.test(usuario)) {
        error.textContent = "Informe seu usuário corporativo ou e-mail.";
        error.hidden = false;
        input.focus();
        return;
      }
      error.hidden = true;
      const saved = salvarIdentificacao(usuario, document.querySelector("#manter-conectado").checked);
      registrarAcesso(usuario);
      // Sem qualquer armazenamento, permite uma entrada sem persistência.
      // O fragmento não contém nome nem senha e não é mecanismo de segurança.
      window.location.assign(destination("index.html") + (saved ? "" : "#entrada-sem-persistencia"));
    });
    return;
  }

  const withoutStorage = window.location.hash === "#entrada-sem-persistencia";
  if (withoutStorage) history.replaceState(null, "", location.pathname + location.search);
  const entry = restaurarIdentificacao();
  window.dashboardAccessGranted = Boolean(entry || withoutStorage);
  if (!window.dashboardAccessGranted) {
    window.location.replace(destination("login.html"));
    return;
  }
  document.documentElement.classList.remove("identificacao-pendente");
  document.querySelector("#sair-dashboard")?.addEventListener("click", () => {
    limparIdentificacao();
    window.location.replace(destination("login.html"));
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted && !restaurarIdentificacao()) window.location.replace(destination("login.html"));
  });
})();
