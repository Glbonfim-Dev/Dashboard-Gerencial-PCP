const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
test('categorias clicaveis, composicao, mes atual, limpeza e volume sem duplicar',()=>{
 const elements=new Map();
 function element(id){if(!elements.has(id))elements.set(id,{value:'',hidden:false,options:[],children:[],listeners:{},attributes:{},textContent:'',replaceChildren(...v){this.children=v;this.options=[];},add(v){this.options.push(v);},append(v){this.children.push(v);},setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,v){this.listeners[k]=v;}});return elements.get(id);}
 const row=(cat,q,id,desc)=>({mes_ref:'2026-11',categoria:cat,componente:cat,quantidade:q,descricao:desc||cat,codigo_produto:id,id_produto:id,conjunto_id:'C1',conjunto_nome:'MOLD FP COMPLETO'});
 const records=[row('MOLDES_FP',2,'GRID'),row('SAPATAS',16,'SPT'),row('CASTELOS',2,'CAST'),row('AUXILIAR',16,'RTD')];
 const data={formato:'pivot_categorias',fim:'2026-11-18',registros:records};
 const ctx={window:{},document:{getElementById:element,createElement:()=>element(Symbol())},Option:function(t,v){this.text=t;this.value=v;},estado:{charts:{}},destruirChart(){},Chart:function(c,config){this.config=config;},mesesQualidade:['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],formatarData:v=>v,Intl,Date,Map,Set};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'..','producao.js'),'utf8'),ctx);
 ctx.window.producaoDashboard.preparar(data);ctx.window.producaoDashboard.renderizar();
 assert.equal(element('producao-mes').value,'11');
 assert.equal(element('producao-total-COMPLETOS').textContent,'2');assert.equal(element('producao-total-MOLDES_FP').textContent,'2');assert.equal(element('producao-total-SAPATAS').textContent,'16');
 element('producao-card-COMPLETOS').listeners.click();assert.equal(element('producao-detalhes').hidden,false);assert.equal(element('producao-itens').children.length,1);
 const accordion=element('producao-itens').children[0];assert.equal(accordion.children[2].children.length,4);
 element('producao-card-SAPATAS').listeners.click();assert.equal(element('producao-itens').children.length,1);assert.equal(element('producao-itens').children[0].children[1].textContent,'16 un.');
 element('producao-mes').value='10';element('producao-mes').listeners.change();assert.equal(element('producao-total-SAPATAS').textContent,'0');
 ctx.window.producaoDashboard.limpar();assert.equal(element('producao-total-SAPATAS').textContent,'16');assert.equal(element('producao-detalhes').hidden,true);
 ctx.window.producaoDashboard.preparar(data);assert.equal(element('producao-mes').value,'');
});
