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

  function emailCorporativoValido(email) {
    return typeof email === "string" && email.length <= 254 && email.split("@")[0].length <= 64 &&
      /^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@colmac\.com$/i.test(email);
  }

  function mensagemEmail(email) {
    if (!email) return "Informe seu e-mail corporativo.";
    if (!email.includes("@")) return 'Inclua um "@" no endereço de e-mail.';
    if (!/@colmac\.com$/i.test(email)) return "Use o domínio @colmac.com.";
    return "Informe um e-mail válido.";
  }

  function limparIdentificacao() {
    stores().forEach((name) => {
      try { window[name].removeItem(ENTRY_KEY); } catch (_) { /* Navegador pode bloquear armazenamento. */ }
    });
  }

  function restaurarIdentificacao() {
    for (const name of stores()) {
      try {
        const saved = JSON.parse(window[name].getItem(ENTRY_KEY) || "null");
        if (saved && emailCorporativoValido(saved.usuario) &&
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
    const emailInput = document.querySelector("#usuario");
    emailInput.addEventListener?.("input", () => {
      emailInput.setCustomValidity?.("");
      document.querySelector("#login-error").hidden = true;
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.querySelector("#usuario");
      const usuario = input.value.trim().toLowerCase();
      const error = document.querySelector("#login-error");
      input.setCustomValidity?.("");
      if (!emailCorporativoValido(usuario)) {
        const message = mensagemEmail(usuario);
        if (input.setCustomValidity && input.reportValidity) {
          error.hidden = true;
          input.setCustomValidity(message);
          input.reportValidity();
        } else {
          error.textContent = message;
          error.hidden = false;
        }
        input.focus();
        return;
      }
      error.hidden = true;
      const saved = salvarIdentificacao(usuario, document.querySelector("#manter-conectado").checked);
      if (!saved) {
        error.textContent = "Permita o armazenamento deste site no navegador e tente novamente.";
        error.hidden = false;
        return;
      }
      registrarAcesso(usuario);
      window.location.assign(destination("index.html"));
    });
    return;
  }

  const entry = restaurarIdentificacao();
  window.dashboardAccessGranted = Boolean(entry);
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
