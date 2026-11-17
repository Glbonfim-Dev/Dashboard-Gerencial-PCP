"use strict";
(() => {
  let fonte = null;
  let selecao = [];
  let preparado = false;
  let rankingAtual = [];
  let chavesTabela = new Set();
  const filtrosTabela = ["busca-item", "tabela-componente", "qtd-min", "qtd-max", "meses-min", "meses-max", "tabela-futura"];
  const el = (id) => document.getElementById(`producao-${id}`);
  const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  const futuro = (r) => ["5922", "6922"].includes(r.cfop);
  const componentes = ["MOLDE COMPLETO", "CASTELO", "GRADE", "SAPATA"];
  const paleta = ["#1769d2", "#00806f", "#13a36f", "#e99a16", "#8b5cf6"];
  function opcoes(id, valores, todos) {
    const select = el(id), anterior = select.value;
    select.replaceChildren();
    if (todos) select.add(new Option(todos, ""));
    valores.forEach((v) => select.add(new Option(v, v)));
    if ([...select.options].some((o) => o.value === anterior)) select.value = anterior;
  }
  function preparar(dados) {
    fonte = dados || { registros: [], avisos: [] };
    const anos = [...new Set(fonte.registros.map((r) => r.mes_ref.slice(0, 4)))].sort();
    opcoes("ano", anos, "Todo o período de 2026");
    opcoes("componente", [...new Set(fonte.registros.map((r) => r.componente))].sort(), "Todos os componentes");
    opcoes("tabela-componente", [...new Set(fonte.registros.map((r) => r.componente))].sort(), "Todos");
    if (!preparado) { el("ano").value = anos.at(-1) || ""; preparado = true; }
    const consolidado = fonte.granularidade === "componente";
    el("moldes-rotulo").textContent = fonte.formato === "estrutura_nf" ? "OS de moldes completos" : "Moldes completos";
    el("castelos-rotulo").textContent = fonte.formato === "estrutura_nf" ? "Castelos na estrutura" : "Castelos · linha própria";
    el("operacao-grupo").hidden = !fonte.operacao_disponivel;
    if (!fonte.operacao_disponivel) el("operacao").value = "";
    el("itens-rotulo").textContent = consolidado ? "Componentes distintos" : "Itens distintos";
    el("ranking-titulo").textContent = fonte.formato === "estrutura_nf" ? "Produtos próprios mais utilizados" : consolidado ? "Componentes mais faturados" : "Itens mais faturados";
    el("recorrencia-titulo").textContent = fonte.formato === "estrutura_nf" ? "Recorrência dos produtos próprios" : consolidado ? "Recorrência dos componentes" : "Recorrência dos itens";
    el("avisos").replaceChildren(...(fonte.avisos || []).map((v) => { const li = document.createElement("li"); li.textContent = v; return li; }));
  }
  function limpar() {
    ["ano", "mes", "componente", "operacao"].forEach((id) => { el(id).value = ""; });
    filtrosTabela.forEach((id) => { el(id).value = ""; });
    renderizar();
  }
  function renderizarTabela() {
    const texto = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const busca = texto(el("busca-item").value.trim());
    const componente = el("tabela-componente").value, entrega = el("tabela-futura").value;
    const limite = (id, padrao) => el(id).value === "" ? padrao : Number(el(id).value);
    const filtrados = rankingAtual.filter((g) => (!busca || texto(g.descricao).includes(busca)) &&
      (!componente || g.componente === componente) &&
      g.quantidade >= limite("qtd-min", -Infinity) && g.quantidade <= limite("qtd-max", Infinity) &&
      g.meses.size >= limite("meses-min", -Infinity) && g.meses.size <= limite("meses-max", Infinity) &&
      (!entrega || (entrega === "nd" ? !fonte.operacao_disponivel : fonte.operacao_disponivel && (entrega === "sim" ? g.futura > 0 : g.futura === 0))));
    chavesTabela = new Set(filtrados.map((g) => g.chave));
    el("tabela").replaceChildren(...filtrados.map((g) => {
      const tr = document.createElement("tr");
      [g.descricao, g.componente, nf.format(g.quantidade), nf.format(g.meses.size), fonte.operacao_disponivel ? nf.format(g.futura) : "Não discriminado"].forEach((v) => { const td = document.createElement("td"); td.textContent = v; tr.append(td); }); return tr;
    }));
    if (!filtrados.length) {
      const tr = document.createElement("tr"), td = document.createElement("td");
      td.colSpan = 5; td.textContent = "Nenhum item encontrado para os filtros da tabela."; tr.append(td); el("tabela").append(tr);
    }
    el("tabela-contagem").textContent = `${nf.format(filtrados.length)} de ${nf.format(rankingAtual.length)} itens.`;
  }
  function grafico(nome, canvas, tipo, labels, datasets, horizontal = false) {
    destruirChart(nome);
    estado.charts[nome] = new Chart(document.getElementById(canvas), {
      type: tipo, data: { labels, datasets }, options: {
        responsive: true, maintainAspectRatio: false, indexAxis: horizontal ? "y" : "x",
        plugins: { legend: { display: !horizontal }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${nf.format(horizontal ? c.parsed.x : c.parsed.y)}` } } },
        scales: { [horizontal ? "x" : "y"]: { beginAtZero: true }, [horizontal ? "y" : "x"]: { ticks: { autoSkip: true, maxTicksLimit: horizontal ? 10 : 12 } } }
      }
    });
  }
  function renderizar() {
    if (!fonte) preparar(estado.dados?.producao);
    const ano = el("ano").value, mes = el("mes").value, comp = el("componente").value, operacao = el("operacao").value;
    selecao = fonte.registros.filter((r) => (!ano || r.mes_ref.startsWith(ano)) && (!mes || r.mes_ref.slice(5) === mes) && (!comp || r.componente === comp) && (!operacao || futuro(r) === (operacao === "futura")));
    el("vazio").hidden = selecao.length > 0;
    el("conteudo").hidden = selecao.length === 0;
    if (!selecao.length) { ["producao-mensal", "producao-ranking"].forEach(destruirChart); return; }
    componentes.forEach((c, i) => { el(["moldes", "castelos", "grades", "sapatas"][i]).textContent = nf.format(selecao.filter((r) => r.componente === c).reduce((s, r) => s + r.quantidade, 0)); });
    if (fonte.formato === "estrutura_nf") el("moldes").textContent = nf.format(new Set(selecao.map((r) => r.os_molde_completo).filter(Boolean)).size);
    const grupos = new Map();
    selecao.forEach((r) => {
      const key = `${r.chave_molde}|${r.componente}`;
      if (!grupos.has(key)) grupos.set(key, { chave: key, descricao: r.descricao, componente: r.componente, quantidade: 0, meses: new Set(), futura: 0 });
      const g = grupos.get(key); g.quantidade += r.quantidade; g.meses.add(r.mes_ref); if (futuro(r)) g.futura += r.quantidade;
    });
    el("itens").textContent = nf.format(grupos.size);
    const ranking = [...grupos.values()].sort((a, b) => b.quantidade - a.quantidade || a.descricao.localeCompare(b.descricao));
    rankingAtual = ranking;
    renderizarTabela();
    // Meses sem linhas permanecem em zero dentro do intervalo coberto pela fonte.
    let meses = (fonte.meses || []).filter((m) => (!ano || m.startsWith(ano)) && (!mes || m.slice(5) === mes));
    if (meses.length) {
      const primeiro = new Date(`${meses[0]}-01T12:00:00Z`), ultimo = meses.at(-1), calendario = [];
      while (primeiro.toISOString().slice(0, 7) <= ultimo) { const m = primeiro.toISOString().slice(0, 7); if (!mes || m.slice(5) === mes) calendario.push(m); primeiro.setUTCMonth(primeiro.getUTCMonth() + 1); }
      meses = calendario;
    }
    const cats = comp ? [comp] : [...new Set(selecao.map((r) => r.componente))].sort();
    grafico("producao-mensal", "grafico-producao-mensal", "bar", meses, cats.map((c, i) => ({ label: c, backgroundColor: paleta[i % paleta.length], data: meses.map((m) => selecao.filter((r) => r.mes_ref === m && r.componente === c).reduce((s, r) => s + r.quantidade, 0)), borderRadius: 4 })));
    grafico("producao-ranking", "grafico-producao-ranking", "bar", ranking.slice(0, 10).map((g) => g.descricao.length > 38 ? `${g.descricao.slice(0, 37)}…` : g.descricao), [{ label: fonte.formato === "estrutura_nf" ? "Quantidade utilizada" : "Unidades faturadas", data: ranking.slice(0, 10).map((g) => g.quantidade), backgroundColor: "#1769d2", borderRadius: 4 }], true);
  }
  for (let m = 1; m <= 12; m++) el("mes").add(new Option(mesesQualidade[m - 1], String(m).padStart(2, "0")));
  ["ano", "mes", "componente", "operacao"].forEach((id) => el(id).addEventListener("change", renderizar));
  el("limpar").addEventListener("click", limpar);
  filtrosTabela.forEach((id) => el(id).addEventListener(["tabela-componente", "tabela-futura"].includes(id) ? "change" : "input", renderizarTabela));
  el("tabela-limpar").addEventListener("click", () => {
    filtrosTabela.forEach((id) => { el(id).value = ""; }); renderizarTabela();
  });
  el("exportar").addEventListener("click", () => {
    const quote = (v) => `"${String(v).replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`;
    const linhas = [["Mês", "Descrição", "Componente", "Quantidade", "CFOP", "NF", "OS principal", "OS fabricação", "Unidade"], ...selecao.filter((r) => chavesTabela.has(`${r.chave_molde}|${r.componente}`)).map((r) => [r.mes_ref, r.descricao, r.componente, r.quantidade.toLocaleString("pt-BR", { useGrouping: false }), r.cfop, r.nf || "", r.os_principal || "", r.os_fabricacao || "", r.unidade || ""])];
    const url = URL.createObjectURL(new Blob(["\ufeff" + linhas.map((r) => r.map(quote).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = "producao-kpi.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.producaoDashboard = { preparar, renderizar, limpar };
  if (estado.dados) preparar(estado.dados.producao);
})();
