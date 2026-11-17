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
    el("operacao-grupo").hidden = !fonte.operacao_disponivel;
    if (!fonte.operacao_disponivel) el("operacao").value = "";
    el("itens-rotulo").textContent = consolidado ? "Componentes distintos" : "Itens distintos";
    el("ranking-titulo").textContent = consolidado ? "Componentes mais faturados" : "Itens mais faturados";
    el("recorrencia-titulo").textContent = consolidado ? "Recorrência dos componentes" : "Recorrência dos itens";
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
    const parcial = (fonte.meses_parciais || []).filter((m) => (!ano || m.startsWith(ano)) && (!mes || m.slice(5) === mes));
    el("fonte").textContent = `Fonte: ${fonte.origem || "não disponível"} · Base: ${fonte.data_base ? formatarAtualizacao(fonte.data_base) : "não informada"} · ${nf.format(selecao.length)} registros na seleção.${parcial.length ? ` Período parcial: ${parcial.join(", ")}.` : ""}`;
    if (!selecao.length) { ["producao-mensal", "producao-ranking"].forEach(destruirChart); return; }
    componentes.forEach((c, i) => { el(["moldes", "castelos", "grades", "sapatas"][i]).textContent = nf.format(selecao.filter((r) => r.componente === c).reduce((s, r) => s + r.quantidade, 0)); });
    const grupos = new Map();
    selecao.forEach((r) => {
      const key = `${r.chave_molde}|${r.componente}`;
      if (!grupos.has(key)) grupos.set(key, { descricao: r.descricao, componente: r.componente, quantidade: 0, meses: new Set(), futura: 0 });
      const g = grupos.get(key); g.quantidade += r.quantidade; g.meses.add(r.mes_ref); if (futuro(r)) g.futura += r.quantidade;
    });
    el("itens").textContent = nf.format(grupos.size);
    const ranking = [...grupos.values()].sort((a, b) => b.quantidade - a.quantidade || a.descricao.localeCompare(b.descricao));
    el("tabela").replaceChildren(...ranking.map((g) => {
      const tr = document.createElement("tr");
      [g.descricao, g.componente, nf.format(g.quantidade), nf.format(g.meses.size), fonte.operacao_disponivel ? nf.format(g.futura) : "Não discriminado"].forEach((v) => { const td = document.createElement("td"); td.textContent = v; tr.append(td); }); return tr;
    }));
    // Meses sem linhas permanecem em zero dentro do intervalo coberto pela fonte.
    let meses = (fonte.meses || []).filter((m) => (!ano || m.startsWith(ano)) && (!mes || m.slice(5) === mes));
    if (meses.length) {
      const primeiro = new Date(`${meses[0]}-01T12:00:00Z`), ultimo = meses.at(-1), calendario = [];
      while (primeiro.toISOString().slice(0, 7) <= ultimo) { const m = primeiro.toISOString().slice(0, 7); if (!mes || m.slice(5) === mes) calendario.push(m); primeiro.setUTCMonth(primeiro.getUTCMonth() + 1); }
      meses = calendario;
    }
    const cats = comp ? [comp] : [...new Set(selecao.map((r) => r.componente))].sort();
    grafico("producao-mensal", "grafico-producao-mensal", "bar", meses, cats.map((c, i) => ({ label: c, backgroundColor: paleta[i % paleta.length], data: meses.map((m) => selecao.filter((r) => r.mes_ref === m && r.componente === c).reduce((s, r) => s + r.quantidade, 0)), borderRadius: 4 })));
    grafico("producao-ranking", "grafico-producao-ranking", "bar", ranking.slice(0, 10).map((g) => g.descricao.length > 38 ? `${g.descricao.slice(0, 37)}…` : g.descricao), [{ label: "Unidades faturadas", data: ranking.slice(0, 10).map((g) => g.quantidade), backgroundColor: "#1769d2", borderRadius: 4 }], true);
  }
  for (let m = 1; m <= 12; m++) el("mes").add(new Option(mesesQualidade[m - 1], String(m).padStart(2, "0")));
  ["ano", "mes", "componente", "operacao"].forEach((id) => el(id).addEventListener("change", renderizar));
  el("limpar").addEventListener("click", limpar);
  el("exportar").addEventListener("click", () => {
    const quote = (v) => `"${String(v).replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`;
    const linhas = [["Mês", "Descrição", "Componente", "Quantidade", "CFOP"], ...selecao.map((r) => [r.mes_ref, r.descricao, r.componente, r.quantidade.toLocaleString("pt-BR", { useGrouping: false }), r.cfop])];
    const url = URL.createObjectURL(new Blob(["\ufeff" + linhas.map((r) => r.map(quote).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = "producao-kpi.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.producaoDashboard = { preparar, renderizar, limpar };
  if (estado.dados) preparar(estado.dados.producao);
})();
