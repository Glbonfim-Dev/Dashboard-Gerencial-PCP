"use strict";
(() => {
  let fonte = null;
  let selecao = [];
  let preparado = false;
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
    if (!preparado) { el("ano").value = anos.at(-1) || ""; preparado = true; }
    const consolidado = fonte.granularidade === "componente";
    el("moldes-rotulo").textContent = fonte.formato === "estrutura_nf" ? "OS de moldes completos" : "Moldes completos";
    el("castelos-rotulo").textContent = fonte.formato === "estrutura_nf" ? "Castelos na estrutura" : "Castelos · linha própria";
    el("operacao-grupo").hidden = !fonte.operacao_disponivel;
    if (!fonte.operacao_disponivel) el("operacao").value = "";
    el("itens-rotulo").textContent = consolidado ? "Componentes distintos" : "Itens distintos";
    el("avisos").replaceChildren(...(fonte.avisos || []).map((v) => { const li = document.createElement("li"); li.textContent = v; return li; }));
  }
  function limpar() {
    ["ano", "mes", "componente", "operacao"].forEach((id) => { el(id).value = ""; });
    renderizar();
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
    if (!selecao.length) { destruirChart("producao-mensal"); return; }
    componentes.forEach((c, i) => { el(["moldes", "castelos", "grades", "sapatas"][i]).textContent = nf.format(selecao.filter((r) => r.componente === c).reduce((s, r) => s + r.quantidade, 0)); });
    if (fonte.formato === "estrutura_nf") el("moldes").textContent = nf.format(new Set(selecao.map((r) => r.os_molde_completo).filter(Boolean)).size);
    el("itens").textContent = nf.format(new Set(selecao.map((r) => `${r.chave_molde}|${r.componente}`)).size);
    // Meses sem linhas permanecem em zero dentro do intervalo coberto pela fonte.
    let meses = (fonte.meses || []).filter((m) => (!ano || m.startsWith(ano)) && (!mes || m.slice(5) === mes));
    if (meses.length) {
      const primeiro = new Date(`${meses[0]}-01T12:00:00Z`), ultimo = meses.at(-1), calendario = [];
      while (primeiro.toISOString().slice(0, 7) <= ultimo) { const m = primeiro.toISOString().slice(0, 7); if (!mes || m.slice(5) === mes) calendario.push(m); primeiro.setUTCMonth(primeiro.getUTCMonth() + 1); }
      meses = calendario;
    }
    const cats = comp ? [comp] : [...new Set(selecao.map((r) => r.componente))].sort();
    grafico("producao-mensal", "grafico-producao-mensal", "bar", meses, cats.map((c, i) => ({ label: c, backgroundColor: paleta[i % paleta.length], data: meses.map((m) => selecao.filter((r) => r.mes_ref === m && r.componente === c).reduce((s, r) => s + r.quantidade, 0)), borderRadius: 4 })));
  }
  for (let m = 1; m <= 12; m++) el("mes").add(new Option(mesesQualidade[m - 1], String(m).padStart(2, "0")));
  ["ano", "mes", "componente", "operacao"].forEach((id) => el(id).addEventListener("change", renderizar));
  el("limpar").addEventListener("click", limpar);
  window.producaoDashboard = { preparar, renderizar, limpar };
  if (estado.dados) preparar(estado.dados.producao);
})();
