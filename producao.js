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
  const ordemComponentes = ["GRADE", "SAPATA", "PLUNGERS", "HD SP/MANIFOLD", "RESIST FUND 600", "RTD ASSY", "INSULATING SPAC", "GROMMET", "AGITADOR", "RASPADOR"];
  const somar = (itens) => itens.reduce((s,r) => s+(Number.isFinite(r.quantidade) ? r.quantidade : 0),0);
  const total = (itens) => itens.length && !itens.some((r) => Number.isFinite(r.quantidade)) ? "—" : nf.format(somar(itens));
  function texto(tag, classe, valor) {
    const node = document.createElement(tag); node.className = classe; node.textContent = valor; return node;
  }
  function icone(tipo) {
    const span = document.createElement("span");
    const simbolo = ({ GRADE: "i-list", SAPATA: "i-check", CASTELO: "i-target" })[tipo] || "i-clipboard";
    span.innerHTML = `<svg aria-hidden="true"><use href="#${simbolo}"></use></svg>`;
    return span;
  }
  function cartaoComponente(tipo, itens, avulso = false) {
    const card = document.createElement("article"); card.className = "production-component-card";
    const title = texto("div", "production-component-name", "");
    title.append(icone(tipo)); title.append(texto("span", "", avulso ? itens[0].descricao_nf || itens[0].descricao : tipo === "SAPATA" ? "SAPATAS" : tipo));
    card.append(title);
    if (avulso) card.append(texto("strong", "", `OS ${itens[0].os_principal || "não informada"}`));
    const known = itens.filter((r) => Number.isFinite(r.quantidade));
    if (avulso && itens.some((r) => r.classificacao === "COMPONENTE_DE_MOLDE")) {
      card.append(texto("small", "", "Outro conjunto identificado nesta nota")); return card;
    }
    if (!avulso || known.length) card.append(texto("strong", "", total(itens)));
    const missing = itens.length-known.length;
    card.append(texto("small", "", known.length ? `${avulso ? "Quantidade informada" : "unidades"}${missing ? ` · ${missing} sem quantidade` : ""}` : "Quantidade não informada"));
    return card;
  }
  function atualizarMoldes(base) {
    const select = el("molde"), anterior = select.value;
    const ids = new Set(base.map((r) => r.molde_id).filter(Boolean));
    select.replaceChildren(); select.add(new Option("Todos os moldes", ""));
    (fonte.moldes || []).filter((m) => ids.has(m.id)).forEach((m) => select.add(new Option(`OS ${m.os_principal || "—"} · NF ${m.nf} · ${m.descricao}`, m.id)));
    select.value = [...select.options].some((o) => o.value === anterior) ? anterior : "";
  }
  function renderizarComposicao(base, selecionados, molde) {
    const grupos = new Map();
    selecionados.filter((r) => r.molde_id).forEach((r) => {
      if (!grupos.has(r.molde_id)) grupos.set(r.molde_id,[]);
      grupos.get(r.molde_id).push(r);
    });
    el("composicao").hidden = !grupos.size;
    el("moldes-cards").replaceChildren(...[...grupos.entries()].map(([id,itens]) => {
      const meta = (fonte.moldes || []).find((m) => m.id === id) || itens[0];
      const parent = document.createElement("article"); parent.className = "panel production-mould-card";
      const heading = document.createElement("div"); heading.className = "production-mould-heading";
      const symbol = document.createElement("span"); symbol.className = "production-mould-icon"; symbol.append(icone("MOLDE COMPLETO"));
      heading.append(symbol); heading.append(texto("h2", "", "Molde completo")); heading.append(texto("span", "production-mould-badge", "1 conjunto identificado")); parent.append(heading);
      parent.append(texto("p", "production-mould-description", meta.descricao_nf || meta.descricao || "Molde completo"));
      parent.append(texto("p", "production-mould-meta", `NF ${meta.nf} · OS principal ${meta.os_principal || "não informada"}`));
      parent.append(texto("h3", "", "Componentes deste molde"));
      const internos = itens.filter((r) => r.classificacao === "COMPONENTE_DE_MOLDE");
      const grid = document.createElement("div"); grid.className = "production-component-grid";
      const tipos = [...new Set(internos.map((r) => r.componente))].sort((a,b) => {
        const ia=ordemComponentes.indexOf(a), ib=ordemComponentes.indexOf(b);
        return (ia<0 ? 99 : ia)-(ib<0 ? 99 : ib) || a.localeCompare(b);
      });
      tipos.forEach((tipo) => grid.append(cartaoComponente(tipo,internos.filter((r) => r.componente===tipo))));
      if (!tipos.length) grid.append(texto("p", "quality-note", "Composição não informada na planilha."));
      parent.append(grid); return parent;
    }));
    const notas = new Set(selecionados.filter((r) => r.molde_id).map((r) => r.nf));
    const fora = base.filter((r) => notas.has(r.nf) && (molde ? r.molde_id !== molde : !r.molde_id));
    const externos = new Map();
    fora.forEach((r) => {
      const key = `${r.nf}|${r.os_principal}|${r.descricao_nf || r.descricao}`;
      if (!externos.has(key)) externos.set(key,[]); externos.get(key).push(r);
    });
    el("fora-molde").hidden = !externos.size || !grupos.size;
    el("fora-titulo").textContent = molde ? "Fora deste molde · mesma NF" : "Outros itens das mesmas notas";
    el("fora-cards").replaceChildren(...[...externos.values()].map((itens) => cartaoComponente(itens[0].componente,itens,true)));
  }
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
    opcoes("nf", [...new Set(fonte.registros.map((r) => r.nf).filter(Boolean))].sort((a,b) => Number(a)-Number(b)), "Todas as notas");
    atualizarMoldes(fonte.registros);
    if (!preparado) { el("ano").value = anos.at(-1) || ""; preparado = true; }
    const consolidado = fonte.granularidade === "componente";
    el("moldes-rotulo").textContent = "Moldes completos";
    el("castelos-rotulo").textContent = fonte.formato === "estrutura_nf" ? "Castelos na estrutura" : "Castelos · linha própria";
    el("operacao-grupo").hidden = !fonte.operacao_disponivel;
    if (!fonte.operacao_disponivel) el("operacao").value = "";
    el("itens-rotulo").textContent = consolidado ? "Componentes distintos" : "Itens distintos";
    el("avisos").replaceChildren(...(fonte.avisos || []).map((v) => { const li = document.createElement("li"); li.textContent = v; return li; }));
  }
  function limpar() {
    ["ano", "mes", "componente", "operacao", "nf", "molde"].forEach((id) => { el(id).value = ""; });
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
    const nota = el("nf").value;
    const base = fonte.registros.filter((r) => (!ano || r.mes_ref.startsWith(ano)) && (!mes || r.mes_ref.slice(5) === mes) && (!operacao || futuro(r) === (operacao === "futura")) && (!nota || r.nf === nota));
    atualizarMoldes(base);
    const molde = el("molde").value;
    selecao = base.filter((r) => (!comp || r.componente === comp) && (!molde || r.molde_id === molde));
    el("visao-geral").hidden = Boolean(molde);
    el("evolucao").hidden = Boolean(molde);
    el("vazio").hidden = selecao.length > 0;
    el("conteudo").hidden = selecao.length === 0;
    if (!selecao.length) { destruirChart("producao-mensal"); return; }
    componentes.forEach((c, i) => {
      const id = ["moldes", "castelos", "grades", "sapatas"][i], itens = selecao.filter((r) => r.componente === c);
      el(id).textContent = total(itens);
      const ausentes = itens.filter((r) => !Number.isFinite(r.quantidade)).length;
      if (i > 0) el(`${id}-nota`).textContent = ausentes ? `${ausentes} registros sem quantidade` : "";
    });
    if (fonte.formato === "estrutura_nf") el("moldes").textContent = nf.format(new Set(selecao.map((r) => r.molde_id || r.os_molde_completo).filter(Boolean)).size);
    el("orientacao").hidden = Boolean(nota || molde);
    if (nota || molde) renderizarComposicao(base,selecao,molde);
    else { el("composicao").hidden = true; el("fora-molde").hidden = true; }
    el("itens").textContent = nf.format(new Set(selecao.map((r) => `${r.chave_molde}|${r.componente}`)).size);
    // Meses sem linhas permanecem em zero dentro do intervalo coberto pela fonte.
    let meses = (fonte.meses || []).filter((m) => (!ano || m.startsWith(ano)) && (!mes || m.slice(5) === mes));
    if (meses.length) {
      const primeiro = new Date(`${meses[0]}-01T12:00:00Z`), ultimo = meses.at(-1), calendario = [];
      while (primeiro.toISOString().slice(0, 7) <= ultimo) { const m = primeiro.toISOString().slice(0, 7); if (!mes || m.slice(5) === mes) calendario.push(m); primeiro.setUTCMonth(primeiro.getUTCMonth() + 1); }
      meses = calendario;
    }
    if (molde) { destruirChart("producao-mensal"); return; }
    const cats = comp ? [comp] : [...new Set(selecao.map((r) => r.componente))].sort();
    grafico("producao-mensal", "grafico-producao-mensal", "bar", meses, cats.map((c, i) => ({ label: c, backgroundColor: paleta[i % paleta.length], data: meses.map((m) => {
      const itens = selecao.filter((r) => r.mes_ref === m && r.componente === c);
      return itens.length && !itens.some((r) => Number.isFinite(r.quantidade)) ? null : itens.reduce((s,r) => s+(Number.isFinite(r.quantidade) ? r.quantidade : 0),0);
    }), borderRadius: 4 })));
  }
  for (let m = 1; m <= 12; m++) el("mes").add(new Option(mesesQualidade[m - 1], String(m).padStart(2, "0")));
  ["ano", "mes", "componente", "operacao", "nf", "molde"].forEach((id) => el(id).addEventListener("change", renderizar));
  el("limpar").addEventListener("click", limpar);
  window.producaoDashboard = { preparar, renderizar, limpar };
  if (estado.dados) preparar(estado.dados.producao);
})();
