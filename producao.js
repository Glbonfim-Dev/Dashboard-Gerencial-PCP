"use strict";
(() => {
  const categorias={COMPLETOS:"Moldes Completos",MOLDES_FP:"Moldes FP",MOLDES_FB:"Moldes FB",SAPATAS:"Sapatas",CASTELOS:"Castelos",CANECOS:"Canecos"};
  const coresCategorias=["#1769d2","#00806f","#13a36f","#e99a16","#8054d9","#437e99"];
  const el=(id)=>document.getElementById(`producao-${id}`);
  const numero=new Intl.NumberFormat("pt-BR",{maximumFractionDigits:2});
  let fonte={registros:[]},inicializado=false,ativa=null;
  const soma=(rows)=>rows.reduce((s,r)=>s+(Number.isFinite(r.quantidade)?r.quantidade:0),0);
  const volume=(rows)=>rows.length&&!rows.some((r)=>Number.isFinite(r.quantidade))?"—":numero.format(soma(rows));
  function node(tag,classe,texto){const n=document.createElement(tag);n.className=classe;n.textContent=texto;return n;}
  function agrupar(rows,chave){const map=new Map();rows.forEach((r)=>{const key=chave(r);if(!map.has(key))map.set(key,[]);map.get(key).push(r);});return map;}
  function conjuntos(rows){
    return [...agrupar(rows.filter((r)=>r.conjunto_id),(r)=>r.conjunto_id).values()].map((items)=>{
      const grids=items.filter((r)=>["MOLDES_FP","MOLDES_FB"].includes(r.categoria));
      const diretos=items.filter((r)=>r.categoria==="COMPLETOS");
      return {descricao:items[0].conjunto_nome,cliente:items[0].cliente,os:items[0].os,mes_ref:items[0].mes_ref,quantidade:diretos.some((r)=>Number.isFinite(r.quantidade))?soma(diretos):grids.some((r)=>Number.isFinite(r.quantidade))?soma(grids):null,componentes:items.filter((r)=>r.categoria!=="COMPLETOS")};
    });
  }
  function itensCategoria(rows,key){
    const base=key==="COMPLETOS"?conjuntos(rows):rows.filter((r)=>r.categoria===key);
    return [...agrupar(base,(r)=>key==="COMPLETOS"?r.descricao:(r.codigo_produto||r.descricao)).values()].map((items)=>({
      descricao:items[0].descricao,quantidade:items.some((r)=>Number.isFinite(r.quantidade))?soma(items):null,
      pendentes:items.filter((r)=>!Number.isFinite(r.quantidade)).length,
      componentes:items.flatMap((r)=>r.componentes||[]),
      origens:[...agrupar(items,(r)=>JSON.stringify([r.cliente||"",r.os||"",r.os_producao||"",r.mes_ref])).values()].map((grupo)=>({cliente:grupo[0].cliente,os:grupo[0].os,os_producao:grupo[0].os_producao,mes_ref:grupo[0].mes_ref,quantidade:grupo.some((r)=>Number.isFinite(r.quantidade))?soma(grupo):null}))
    })).sort((a,b)=>(b.quantidade||0)-(a.quantidade||0)||a.descricao.localeCompare(b.descricao));
  }
  function renderizarOrigens(item,completo=false){
    const lista=node("div","production-origins","");
    item.origens.forEach((origem)=>{
      const linha=node("div","production-origin","");
      linha.append(node("span","production-origin-client",`Cliente: ${origem.cliente||"Não informado"}`));
      linha.append(node("span","production-origin-os",`OS: ${origem.os||"Não informada"}`));
      if(origem.os_producao&&origem.os_producao!==origem.os)linha.append(node("span","production-origin-os",`Fabricação: ${origem.os_producao}`));
      if(!el("mes").value)linha.append(node("span","production-origin-month",`${mesesQualidade[Number(origem.mes_ref.slice(5))-1]} / 2026`));
      linha.append(node("span","production-origin-quantity",origem.quantidade===null?"Quantidade não informada":`${numero.format(origem.quantidade)} ${completo?"conjuntos":"un."}`));
      lista.append(linha);
    });
    return lista;
  }
  function preparar(dados){
    fonte=dados?.formato==="pivot_categorias"?dados:{registros:[],fim:"",formato:"aguardando"};
    const anterior=el("mes").value;
    el("mes").replaceChildren();el("mes").add(new Option("Janeiro até a data atual",""));
    const fim=fonte.fim||new Intl.DateTimeFormat("sv-SE",{timeZone:"America/Sao_Paulo"}).format(new Date());
    const ultimo=fim.startsWith("2026")?Number(fim.slice(5,7)):12;
    for(let i=1;i<=ultimo;i++)el("mes").add(new Option(mesesQualidade[i-1],String(i).padStart(2,"0")));
    if(!inicializado){el("mes").value=fim.startsWith("2026")?fim.slice(5,7):"";inicializado=true;}
    else el("mes").value=[...el("mes").options].some((o)=>o.value===anterior)?anterior:"";
  }
  function renderizarDetalhes(rows){
    el("detalhes").hidden=!ativa;
    Object.keys(categorias).forEach((k)=>{el(`card-${k}`).setAttribute("aria-expanded",String(ativa===k));});
    if(!ativa)return;
    const label=el("mes").value?`${mesesQualidade[Number(el("mes").value)-1]} / 2026`:"Janeiro até a data atual / 2026";
    el("detalhes-titulo").textContent=`${categorias[ativa]} · ${label}`;
    const list=itensCategoria(rows,ativa);
    const cards=list.map((item)=>{
      if(ativa!=="COMPLETOS"){
        const article=node("article","production-item-row","");article.append(node("span","",item.descricao));article.append(node("strong","",item.quantidade===null?"Quantidade não informada":`${numero.format(item.quantidade)} un.${item.pendentes?" · parcial":""}`));article.append(renderizarOrigens(item));return article;
      }
      const details=document.createElement("details");details.className="production-accordion";
      const summary=document.createElement("summary");summary.append(node("span","",item.descricao));summary.append(node("strong","production-mould-badge",item.quantidade===null?"Volume a confirmar":`${numero.format(item.quantidade)} conjuntos${item.pendentes?" · parcial":""}`));details.append(summary);
      details.append(node("h3","production-component-heading","Componentes deste item"));
      const grid=node("div","production-component-grid","");
      if(!item.componentes.length)grid.append(node("p","quality-note","Nenhum componente com conclusão e faturamento no mesmo mês nesta base."));
      [...agrupar(item.componentes,(r)=>r.componente).entries()].forEach(([nome,items])=>{
        const card=node("article","production-component-card","");card.append(node("span","production-component-name",nome));card.append(node("strong","",volume(items)));card.append(node("small","",items.some((r)=>r.quantidade===null)?"Subtotal informado · há quantidades pendentes":"unidades"));grid.append(card);
      });details.append(grid);details.append(renderizarOrigens(item,true));return details;
    });
    el("itens").replaceChildren(...(cards.length?cards:[node("p","quality-note","Nenhum item nesta categoria no período.")]));
  }
  function renderizarGraficos(rows,mes){
    destruirChart("producao-mensal");
    const fim=fonte.fim||new Intl.DateTimeFormat("sv-SE",{timeZone:"America/Sao_Paulo"}).format(new Date());
    const ultimo=Math.min(12,Math.max(1,Number(fim.slice(5,7))));
    const meses=Array.from({length:ultimo},(_,i)=>`2026-${String(i+1).padStart(2,"0")}`).filter((m)=>!mes||m.slice(5)===mes);
    el("periodo-graficos").textContent=mes?`${mesesQualidade[Number(mes)-1]} · 2026`:`Janeiro a ${mesesQualidade[ultimo-1]} · 2026`;
    const hoje=new Intl.DateTimeFormat("sv-SE",{timeZone:"America/Sao_Paulo"}).format(new Date());
    const parcial=fim.slice(0,7)===hoje.slice(0,7)&&(!mes||mes===fim.slice(5,7));
    el("mes-parcial").hidden=!parcial;el("mes-parcial").textContent=`${mesesQualidade[ultimo-1]} parcial`;
    Object.entries(categorias).forEach(([key,label],i)=>{
      const nome=`producao-mensal-${key}`;destruirChart(nome);
      const items=itensCategoria(rows,key);el(`soma-${key}`).textContent=volume(items);
      const data=meses.map((m)=>{const v=itensCategoria(rows.filter((r)=>r.mes_ref===m),key);return v.length&&!v.some((r)=>Number.isFinite(r.quantidade))?null:soma(v);});
      const maior=Math.max(0,...data.filter(Number.isFinite));
      const base=10**Math.floor(Math.log10(maior||1));
      const max=[1,2,5,10].map((v)=>v*base).find((v)=>v>=maior*1.12)||base*10;
      el(`escala-${key}`).textContent=`Escala: 0–${numero.format(max)} un.`;
      const valores={id:"valoresMensais",afterDatasetsDraw(chart){
        const {ctx,chartArea}=chart;ctx.save();ctx.fillStyle="#071a33";ctx.font="600 12px Geist, Arial, sans-serif";ctx.textAlign="center";ctx.textBaseline="bottom";
        chart.getDatasetMeta(0).data.forEach((bar,index)=>{const value=data[index];if(Number.isFinite(value))ctx.fillText(numero.format(value),bar.x,Math.max(chartArea.top+14,bar.y-5));});ctx.restore();
      }};
      const canvas=document.getElementById(`grafico-producao-${key}`);
      canvas.setAttribute("aria-label",`${label}: ${meses.map((m,j)=>`${mesesQualidade[Number(m.slice(5))-1]} ${data[j]===null?"sem quantidade":numero.format(data[j])}`).join(", ")}`);
      estado.charts[nome]=new Chart(canvas,{type:"bar",plugins:[valores],data:{labels:meses.map((m)=>mesesQualidade[Number(m.slice(5))-1]),datasets:[{label,data,borderRadius:4,maxBarThickness:32,backgroundColor:meses.map((m)=>parcial&&m===fim.slice(0,7)?`${coresCategorias[i]}70`:coresCategorias[i])}]},options:{responsive:true,maintainAspectRatio:false,layout:{padding:{top:18}},scales:{y:{beginAtZero:true,max,ticks:{precision:maior%1?2:0,maxTicksLimit:5},grid:{color:"#d7e1ea"}},x:{grid:{display:false},ticks:{autoSkip:false,maxRotation:0,font:{size:11}}}},plugins:{legend:{display:false},tooltip:{callbacks:{label:(c)=>`${label}: ${numero.format(c.parsed.y)}`}}}}});
    });
  }
  function renderizar(){
    const mes=el("mes").value;
    const rows=fonte.registros.filter((r)=>r.mes_ref.startsWith("2026-")&&(!mes||r.mes_ref.slice(5)===mes));
    el("vazio").hidden=rows.length>0;
    el("estado").textContent=fonte.formato==="aguardando"?"Aguardando a nova base do CPS.":`Período da base: 01/01/2026 a ${formatarData(fonte.fim)}. Mês atual parcial.`;
    Object.keys(categorias).forEach((key)=>{
      const items=itensCategoria(rows,key);el(`total-${key}`).textContent=volume(items);
    });renderizarDetalhes(rows);
    renderizarGraficos(rows,mes);
  }
  function limpar(){el("mes").value="";ativa=null;renderizar();}
  Object.keys(categorias).forEach((key)=>el(`card-${key}`).addEventListener("click",()=>{ativa=ativa===key?null:key;renderizar();}));
  el("fechar").addEventListener("click",()=>{ativa=null;renderizar();});
  el("mes").addEventListener("change",renderizar);el("limpar").addEventListener("click",limpar);
  window.producaoDashboard={preparar,renderizar,limpar};
  if(estado.dados)preparar(estado.dados.producao);
})();
