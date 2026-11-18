"use strict";
(() => {
  const categorias={COMPLETOS:"Moldes Completos",MOLDES_FP:"Moldes FP",MOLDES_FB:"Moldes FB",SAPATAS:"Sapatas",CASTELOS:"Castelos"};
  const coresCategorias=["#1769d2","#00806f","#13a36f","#e99a16","#8054d9"];
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
      return {descricao:items[0].conjunto_nome,quantidade:grids.some((r)=>Number.isFinite(r.quantidade))?soma(grids):null,componentes:items};
    });
  }
  function itensCategoria(rows,key){
    const base=key==="COMPLETOS"?conjuntos(rows):rows.filter((r)=>r.categoria===key);
    return [...agrupar(base,(r)=>key==="COMPLETOS"?r.descricao:(r.codigo_produto||r.descricao)).values()].map((items)=>({
      descricao:items[0].descricao,quantidade:items.some((r)=>Number.isFinite(r.quantidade))?soma(items):null,
      pendentes:items.filter((r)=>!Number.isFinite(r.quantidade)).length,
      componentes:items.flatMap((r)=>r.componentes||[])
    })).sort((a,b)=>(b.quantidade||0)-(a.quantidade||0)||a.descricao.localeCompare(b.descricao));
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
        const article=node("article","production-item-row","");article.append(node("span","",item.descricao));article.append(node("strong","",item.quantidade===null?"Quantidade não informada":`${numero.format(item.quantidade)} un.${item.pendentes?" · parcial":""}`));return article;
      }
      const details=document.createElement("details");details.className="production-accordion";
      const summary=document.createElement("summary");summary.append(node("span","",item.descricao));summary.append(node("strong","production-mould-badge",item.quantidade===null?"Volume a confirmar":`${numero.format(item.quantidade)} conjuntos${item.pendentes?" · parcial":""}`));details.append(summary);
      details.append(node("h3","production-component-heading","Componentes deste item"));
      const grid=node("div","production-component-grid","");
      [...agrupar(item.componentes,(r)=>r.componente).entries()].forEach(([nome,items])=>{
        const card=node("article","production-component-card","");card.append(node("span","production-component-name",nome));card.append(node("strong","",volume(items)));card.append(node("small","",items.some((r)=>r.quantidade===null)?"Subtotal informado · há quantidades pendentes":"unidades"));grid.append(card);
      });details.append(grid);return details;
    });
    el("itens").replaceChildren(...(cards.length?cards:[node("p","quality-note","Nenhum item nesta categoria no período.")]));
  }
  function renderizar(){
    const mes=el("mes").value;
    const rows=fonte.registros.filter((r)=>r.mes_ref.startsWith("2026-")&&(!mes||r.mes_ref.slice(5)===mes));
    el("vazio").hidden=rows.length>0;
    el("estado").textContent=fonte.formato==="aguardando"?"Aguardando a nova base do CPS.":`Período da base: 01/01/2026 a ${formatarData(fonte.fim)}. Mês atual parcial.`;
    Object.keys(categorias).forEach((key)=>{
      const items=itensCategoria(rows,key);el(`total-${key}`).textContent=volume(items);
    });renderizarDetalhes(rows);
    destruirChart("producao-mensal");
    if(!rows.length)return;
    const fim=Number((fonte.fim||"2026-11-18").slice(5,7));
    const meses=Array.from({length:fim},(_,i)=>`2026-${String(i+1).padStart(2,"0")}`).filter((m)=>!mes||m.slice(5)===mes);
    estado.charts["producao-mensal"]=new Chart(document.getElementById("grafico-producao-mensal"),{type:"bar",data:{labels:meses.map((m)=>mesesQualidade[Number(m.slice(5))-1]),datasets:Object.entries(categorias).map(([key,label],i)=>({label,backgroundColor:coresCategorias[i],borderRadius:4,data:meses.map((m)=>{const items=itensCategoria(rows.filter((r)=>r.mes_ref===m),key);return items.length&&!items.some((r)=>Number.isFinite(r.quantidade))?null:soma(items);})}))},options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true}},plugins:{tooltip:{callbacks:{label:(c)=>`${c.dataset.label}: ${numero.format(c.parsed.y)}`}}}}});
  }
  function limpar(){el("mes").value="";ativa=null;renderizar();}
  Object.keys(categorias).forEach((key)=>el(`card-${key}`).addEventListener("click",()=>{ativa=ativa===key?null:key;renderizar();}));
  el("fechar").addEventListener("click",()=>{ativa=null;renderizar();});
  el("mes").addEventListener("change",renderizar);el("limpar").addEventListener("click",limpar);
  window.producaoDashboard={preparar,renderizar,limpar};
  if(estado.dados)preparar(estado.dados.producao);
})();
