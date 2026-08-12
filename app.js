"use strict";

// Estado único da tela: dados carregados, filtros ativos e gráficos Chart.js.
const estado = { dados: null, filtradas: [], charts: {}, mesFaturamentoSelecionado: null };
const INTERVALO_ATUALIZACAO_MS = 60 * 1000;
let atualizacaoEmAndamento = false;

// Paleta compartilhada pelos gráficos para acompanhar as variáveis do CSS.
const cores = { azul: "#1769d2", verde: "#13a36f", laranja: "#e99a16", vermelho: "#d83a3a", teal: "#00806f", grade: "#dfe7ee", texto: "#5d6b7c" };

// Atalhos de DOM e formatadores brasileiros reutilizados em toda a página.
const $ = (seletor) => document.querySelector(seletor);
const numeroBR = new Intl.NumberFormat("pt-BR");
const moedaBR = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

function formatarData(valor) {
  if (!valor) return "—";
  const partes = valor.slice(0, 10).split("-");
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : valor;
}

function formatarAtualizacao(valor) {
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function preencherSelect(seletor, valores) {
  const select = $(seletor);
  const valorAtual = select.value;
  select.querySelectorAll("option:not(:first-child)").forEach((option) => option.remove());
  valores.forEach((valor) => {
    const option = document.createElement("option");
    option.value = String(valor);
    option.textContent = String(valor);
    select.append(option);
  });
  if ([...select.options].some((option) => option.value === valorAtual)) select.value = valorAtual;
}

// Abre ou recolhe a barra lateral e memoriza a preferência do usuário.
function definirEstadoFiltros(aberto, salvar = true) {
  const shell = $("#app-shell");
  const botao = $("#alternar-filtros");
  shell.classList.toggle("filters-collapsed", !aberto);
  botao.setAttribute("aria-expanded", String(aberto));
  botao.title = aberto ? "Ocultar filtros" : "Mostrar filtros";
  if (salvar) localStorage.setItem("dashboard-filtros-abertos", String(aberto));
  window.setTimeout(() => Object.values(estado.charts).forEach((chart) => chart.resize()), 320);
}

// ---------------------------------------------------------------------------
// Filtros gerais e indicadores de ações
// ---------------------------------------------------------------------------

function resumirAcoes(acoes) {
  const resumo = { total: acoes.length, implementadas: 0, andamento: 0, naoIniciadas: 0 };
  acoes.forEach((acao) => {
    if (acao.status === "Implementada") resumo.implementadas += 1;
    else if (acao.status === "Em Andamento") resumo.andamento += 1;
    else if (acao.status === "Não Iniciada") resumo.naoIniciadas += 1;
  });
  resumo.percentual = resumo.total ? (resumo.implementadas / resumo.total) * 100 : 0;
  return resumo;
}

function aplicarFiltros() {
  const responsavel = $("#filtro-responsavel").value;
  const status = $("#filtro-status").value;
  const periodo = $("#filtro-periodo").value;
  estado.filtradas = estado.dados.lista_acoes.filter((acao) =>
    (!responsavel || acao.responsavel === responsavel) &&
    (!status || acao.status === status) &&
    (!periodo || String(acao.ano) === periodo)
  );
  renderizarTudo();
}

function renderizarKPIs() {
  const resumo = resumirAcoes(estado.filtradas);
  $("#kpi-total").textContent = numeroBR.format(resumo.total);
  $("#kpi-implementadas").textContent = numeroBR.format(resumo.implementadas);
  $("#kpi-andamento").textContent = numeroBR.format(resumo.andamento);
  $("#kpi-nao-iniciadas").textContent = numeroBR.format(resumo.naoIniciadas);
  $("#kpi-percentual").textContent = `${resumo.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function destruirChart(nome) {
  if (estado.charts[nome]) estado.charts[nome].destroy();
}

// Plugin simples que escreve o total no centro do gráfico de rosca.
const textoCentral = {
  id: "textoCentral",
  afterDraw(chart) {
    if (chart.config.type !== "doughnut") return;
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const total = chart.data.datasets[0].data.reduce((soma, valor) => soma + Number(valor), 0);
    const x = (chartArea.left + chartArea.right) / 2;
    const y = (chartArea.top + chartArea.bottom) / 2;
    ctx.save();
    ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = "#082552";
    ctx.font = "700 25px Segoe UI"; ctx.fillText(total, x, y - 7);
    ctx.fillStyle = "#68778d"; ctx.font = "12px Segoe UI"; ctx.fillText("Total", x, y + 16);
    ctx.restore();
  }
};

// A fatia define o status do modal; responsável e período definem o escopo.
function renderizarStatus() {
  destruirChart("status");
  const r = resumirAcoes(estado.filtradas);
  estado.charts.status = new Chart($("#grafico-status"), {
    type: "doughnut",
    data: { labels: ["Implementadas", "Em Andamento", "Não Iniciadas"], datasets: [{ data: [r.implementadas, r.andamento, r.naoIniciadas], backgroundColor: [cores.verde, cores.laranja, cores.vermelho], borderColor: "#fff", borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: "57%", onClick(evento, elementos) { if (elementos.length) abrirAcoesPorStatus(elementos[0].index); }, onHover(evento, elementos, chart) { chart.canvas.style.cursor = elementos.length ? "pointer" : "default"; }, plugins: { legend: { position: "right", onClick(evento, item) { abrirAcoesPorStatus(item.index); }, labels: { usePointStyle: true, pointStyle: "circle", boxWidth: 9, padding: 18, color: "#243147", generateLabels(chart) { const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0); return chart.data.labels.map((label, i) => { const valor = chart.data.datasets[0].data[i]; const pct = total ? (valor / total * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : "0"; return { text: `${label}\n${valor} (${pct}%)`, fillStyle: chart.data.datasets[0].backgroundColor[i], strokeStyle: "transparent", hidden: false, index: i, pointStyle: "circle" }; }); } } }, tooltip: { callbacks: { afterBody: () => "Clique para abrir estas ações", label(ctx) { const total = ctx.dataset.data.reduce((a, b) => a + b, 0); const pct = total ? ctx.raw / total * 100 : 0; return ` ${ctx.label}: ${ctx.raw} (${pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%)`; } } } } },
    plugins: [textoCentral]
  });
}

// Gráfico de responsáveis. Barras e nomes são clicáveis para abrir as ações.
function renderizarResponsaveis() {
  destruirChart("responsaveis");
  const contagem = new Map();
  estado.filtradas.forEach((acao) => contagem.set(acao.responsavel, (contagem.get(acao.responsavel) || 0) + 1));
  const itens = [...contagem.entries()].sort((a, b) => b[1] - a[1]);
  estado.charts.responsaveis = new Chart($("#grafico-responsaveis"), {
    type: "bar",
    data: { labels: itens.map(([nome]) => nome), datasets: [{ data: itens.map(([, qtd]) => qtd), backgroundColor: cores.azul, borderRadius: 4, maxBarThickness: 46 }] },
    options: { responsive: true, maintainAspectRatio: false, onClick(evento, elementos, chart) { let indice = elementos[0]?.index; if (!Number.isInteger(indice)) { const escala = chart.scales.x; if (evento.y >= escala.top && evento.y <= escala.bottom) { const distancias = itens.map((_, i) => Math.abs(evento.x - escala.getPixelForTick(i))); const menor = Math.min(...distancias); const limite = itens.length > 1 ? Math.abs(escala.getPixelForTick(1) - escala.getPixelForTick(0)) / 2 : 40; if (menor <= limite) indice = distancias.indexOf(menor); } } if (Number.isInteger(indice) && itens[indice]) abrirAcoesResponsavel(itens[indice][0]); }, onHover(evento, elementos, chart) { const escala = chart.scales.x; const sobreRotulos = evento.y >= escala.top && evento.y <= escala.bottom; chart.canvas.style.cursor = elementos.length || sobreRotulos ? "pointer" : "default"; }, plugins: { legend: { display: false }, tooltip: { callbacks: { afterBody: () => "Clique para ver todas as ações" } } }, scales: { x: { grid: { display: false }, ticks: { color: cores.texto, maxRotation: 45, minRotation: 0 } }, y: { beginAtZero: true, ticks: { precision: 0, color: cores.texto }, grid: { color: cores.grade }, title: { display: true, text: "Quantidade de Ações" } } } }
  });
}

// ---------------------------------------------------------------------------
// Faturamento mensal e comparação Meta x Realizado
// ---------------------------------------------------------------------------

function faturamentoDoFiltro() {
  const periodo = $("#filtro-periodo").value;
  return !periodo || Number(periodo) === estado.dados.faturamento.ano ? estado.dados.faturamento : { ...estado.dados.faturamento, meta_total: 0, realizado_total: 0, percentual_atingimento: 0, mensal: estado.dados.faturamento.mensal.map((m) => ({ ...m, meta: 0, realizado: 0 })) };
}

function renderizarMeta() {
  const fat = faturamentoDoFiltro();
  const referenciaPadrao = fat.referencia_mensal || { mes: "", meta: 0, realizado: 0, percentual_atingimento: 0 };
  const itemSelecionado = Number.isInteger(estado.mesFaturamentoSelecionado) ? fat.mensal[estado.mesFaturamentoSelecionado] : null;
  const referencia = itemSelecionado ? {
    ...itemSelecionado,
    percentual_atingimento: itemSelecionado.meta ? itemSelecionado.realizado / itemSelecionado.meta * 100 : 0
  } : referenciaPadrao;
  const maximo = Math.max(referencia.meta, referencia.realizado, 1);
  $("#mes-referencia").textContent = referencia.mes ? `– ${referencia.mes}` : "";
  $("#rotulo-realizado").textContent = referencia.mes ? `Realizado em ${referencia.mes}` : "Realizado no mês";
  $("#valor-meta").textContent = fat.meta_disponivel ? moedaBR.format(referencia.meta) : "Não configurada";
  $("#valor-realizado").textContent = moedaBR.format(referencia.realizado);
  $("#valor-atingimento").textContent = fat.meta_disponivel ? `${referencia.percentual_atingimento.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%` : "—";
  $("#barra-meta").style.width = `${referencia.meta / maximo * 100}%`;
  $("#barra-realizado").style.width = `${referencia.realizado / maximo * 100}%`;
  $("#barra-atingimento").style.width = `${Math.min(referencia.percentual_atingimento, 100)}%`;
  $("#aviso-meta").hidden = fat.meta_disponivel;
}

// O clique em um ponto mensal atualiza o quadro Meta x Realizado.
function renderizarFaturamento() {
  destruirChart("faturamento");
  const fat = faturamentoDoFiltro();
  $("#ano-faturamento").textContent = fat.ano;
  estado.charts.faturamento = new Chart($("#grafico-faturamento"), {
    type: "line",
    data: { labels: fat.mensal.map((m) => m.mes), datasets: [
      { label: "Meta (R$)", data: fat.mensal.map((m) => m.meta), borderColor: cores.azul, backgroundColor: cores.azul, borderWidth: 2, pointRadius: (ctx) => ctx.dataIndex === estado.mesFaturamentoSelecionado ? 7 : 4, pointBorderWidth: (ctx) => ctx.dataIndex === estado.mesFaturamentoSelecionado ? 3 : 0, pointBorderColor: "#ffffff", tension: 0.22 },
      { label: "Realizado (R$)", data: fat.mensal.map((m) => m.realizado), borderColor: cores.teal, backgroundColor: cores.teal, borderWidth: 2, pointRadius: (ctx) => ctx.dataIndex === estado.mesFaturamentoSelecionado ? 7 : 4, pointBorderWidth: (ctx) => ctx.dataIndex === estado.mesFaturamentoSelecionado ? 3 : 0, pointBorderColor: "#ffffff", tension: 0.22 }
    ] },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, onClick(evento, elementos, chart) { if (!elementos.length) return; estado.mesFaturamentoSelecionado = elementos[0].index; renderizarMeta(); chart.update("none"); }, onHover(evento, elementos, chart) { chart.canvas.style.cursor = elementos.length ? "pointer" : "default"; }, plugins: { legend: { align: "start", labels: { usePointStyle: true, pointStyle: "circle" } }, tooltip: { callbacks: { afterBody: () => "Clique para comparar este mês", label: (ctx) => `${ctx.dataset.label}: ${moedaBR.format(ctx.raw)}` } } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: cores.grade }, ticks: { callback: (v) => moedaBR.format(v).replace("R$ ", "R$ ") } } } }
  });
}

// ---------------------------------------------------------------------------
// Tabelas, badges e janela de detalhamento
// ---------------------------------------------------------------------------

function criarBadge(acao, considerarAtraso = true) {
  const span = document.createElement("span");
  if (considerarAtraso && acao.atrasada) { span.textContent = "Atrasada"; span.className = "badge badge-overdue"; }
  else if (acao.status === "Implementada") { span.textContent = acao.status; span.className = "badge badge-done"; }
  else if (acao.status === "Em Andamento") { span.textContent = acao.status; span.className = "badge badge-progress"; }
  else { span.textContent = acao.status; span.className = "badge badge-pending"; }
  return span;
}

function adicionarCelula(linha, texto, classe = "") {
  const td = document.createElement("td"); td.textContent = texto || "—"; if (classe) td.className = classe; linha.append(td); return td;
}

function prazoExibido(acao) { return acao.prazo ? formatarData(acao.prazo) : (acao.prazo_texto || "—"); }

function renderizarAtencao() {
  const tbody = $("#tabela-atencao"); tbody.replaceChildren();
  const criticas = estado.filtradas
    .filter((a) => a.atrasada || a.status === "Não Iniciada" || a.proxima_vencimento)
    .sort((a, b) => Number(b.atrasada) - Number(a.atrasada) || String(a.prazo || "9999").localeCompare(String(b.prazo || "9999")))
    .slice(0, 7);
  if (!criticas.length) { const tr = document.createElement("tr"); const td = adicionarCelula(tr, "Nenhuma ação crítica nos filtros selecionados", "empty-row"); td.colSpan = 4; tbody.append(tr); return; }
  criticas.forEach((acao) => { const tr = document.createElement("tr"); adicionarCelula(tr, acao.acao); adicionarCelula(tr, acao.responsavel); adicionarCelula(tr, prazoExibido(acao), acao.atrasada ? "date-overdue" : (acao.proxima_vencimento ? "date-soon" : "")); const td = document.createElement("td"); td.append(criarBadge(acao)); tr.append(td); tbody.append(tr); });
}

function renderizarTabelaCompleta(acoes = estado.filtradas, titulo = "Todas as ações") {
  const tbody = $("#tabela-todas"); tbody.replaceChildren();
  if (!acoes.length) {
    const tr = document.createElement("tr");
    const td = adicionarCelula(tr, "Nenhuma ação encontrada para esta seleção", "empty-row");
    td.colSpan = 6;
    tbody.append(tr);
  }
  acoes.forEach((acao) => { const tr = document.createElement("tr"); adicionarCelula(tr, acao.acao); adicionarCelula(tr, acao.responsavel); adicionarCelula(tr, prazoExibido(acao), acao.atrasada ? "date-overdue" : ""); const status = document.createElement("td"); status.append(criarBadge(acao, false)); tr.append(status); adicionarCelula(tr, acao.observacao); adicionarCelula(tr, formatarData(acao.data_conclusao)); tbody.append(tr); });
  const resumo = resumirAcoes(acoes);
  $("#modal-titulo").textContent = titulo;
  $("#modal-resumo").textContent = `${resumo.total} ações • ${resumo.implementadas} implementadas • ${resumo.andamento} em andamento • ${resumo.naoIniciadas} não iniciadas`;
}

function abrirModalAcoes(acoes, titulo) {
  renderizarTabelaCompleta(acoes, titulo);
  $("#modal-acoes").showModal();
}

function abrirAcoesResponsavel(responsavel) {
  const ordemStatus = { "Não Iniciada": 0, "Em Andamento": 1, "Implementada": 2 };
  const acoes = estado.dados.lista_acoes
    .filter((acao) => acao.responsavel === responsavel)
    .sort((a, b) => (ordemStatus[a.status] ?? 3) - (ordemStatus[b.status] ?? 3) || String(a.prazo || "9999").localeCompare(String(b.prazo || "9999")));
  abrirModalAcoes(acoes, `Ações de ${responsavel}`);
}

function abrirAcoesPorStatus(indiceStatus) {
  const responsavel = $("#filtro-responsavel").value;
  const status = ["Implementada", "Em Andamento", "Não Iniciada"][indiceStatus];
  if (!status) return;
  const periodo = $("#filtro-periodo").value;
  const rotulos = { "Implementada": "Implementadas", "Em Andamento": "Em Andamento", "Não Iniciada": "Não Iniciadas" };
  const acoes = estado.dados.lista_acoes
    .filter((acao) => acao.status === status)
    .filter((acao) => !responsavel || acao.responsavel === responsavel)
    .filter((acao) => !periodo || String(acao.ano) === periodo)
    .sort((a, b) => String(a.prazo || "9999").localeCompare(String(b.prazo || "9999")));
  const escopo = responsavel || "Todos os responsáveis";
  abrirModalAcoes(acoes, `${rotulos[status]} – ${escopo}`);
}

// Atualiza todos os componentes depois de qualquer mudança nos filtros gerais.
function renderizarTudo() { renderizarKPIs(); renderizarStatus(); renderizarResponsaveis(); renderizarMeta(); renderizarFaturamento(); renderizarAtencao(); renderizarTabelaCompleta(); }

// ---------------------------------------------------------------------------
// Inicialização da página e eventos do usuário
// ---------------------------------------------------------------------------

async function atualizarDados() {
  if (atualizacaoEmAndamento) return;
  atualizacaoEmAndamento = true;
  try {
    const resposta = await fetch(`./dados.json?ts=${Date.now()}`, { cache: "no-store" });
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    const novosDados = await resposta.json();
    if (!Array.isArray(novosDados.lista_acoes)) throw new Error("dados.json não contém lista_acoes");
    if (estado.dados?.ultima_atualizacao === novosDados.ultima_atualizacao) {
      $("#mensagem-erro").hidden = true;
      return;
    }

    const mesAnterior = estado.mesFaturamentoSelecionado === null
      ? null
      : estado.dados?.faturamento?.mensal?.[estado.mesFaturamentoSelecionado]?.mes;
    estado.dados = novosDados;
    $("#ultima-atualizacao").textContent = formatarAtualizacao(estado.dados.ultima_atualizacao);
    preencherSelect("#filtro-responsavel", [...new Set(estado.dados.lista_acoes.map((a) => a.responsavel))].sort());
    preencherSelect("#filtro-status", [...new Set(estado.dados.lista_acoes.map((a) => a.status))].sort());
    preencherSelect("#filtro-periodo", estado.dados.periodos || []);

    const mesPreferido = mesAnterior || estado.dados.faturamento.referencia_mensal?.mes;
    estado.mesFaturamentoSelecionado = estado.dados.faturamento.mensal.findIndex((item) => item.mes === mesPreferido);
    if (estado.mesFaturamentoSelecionado < 0) estado.mesFaturamentoSelecionado = null;
    $("#mensagem-erro").hidden = true;
    aplicarFiltros();
  } catch (erro) {
    const banner = $("#mensagem-erro");
    banner.hidden = false;
    banner.textContent = `Não foi possível atualizar os dados: ${erro.message}. Nova tentativa automática em 1 minuto.`;
  } finally {
    atualizacaoEmAndamento = false;
  }
}

// Liga os controles do HTML às funções de filtragem, modal e painel lateral.
["#filtro-responsavel", "#filtro-status", "#filtro-periodo"].forEach((id) => $(id).addEventListener("change", aplicarFiltros));
$("#limpar-filtros").addEventListener("click", () => { $("#filtro-responsavel").value = ""; $("#filtro-status").value = ""; $("#filtro-periodo").value = ""; aplicarFiltros(); });
$("#alternar-filtros").addEventListener("click", () => definirEstadoFiltros($("#app-shell").classList.contains("filters-collapsed")));
$("#ver-todas").addEventListener("click", () => abrirModalAcoes(estado.filtradas, "Todas as ações"));
$("#fechar-modal").addEventListener("click", () => $("#modal-acoes").close());
$("#modal-acoes").addEventListener("click", (evento) => { if (evento.target === $("#modal-acoes")) $("#modal-acoes").close(); });
definirEstadoFiltros(localStorage.getItem("dashboard-filtros-abertos") === "true", false);
atualizarDados();
window.setInterval(atualizarDados, INTERVALO_ATUALIZACAO_MS);
