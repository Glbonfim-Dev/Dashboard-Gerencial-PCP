const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('filtros de outubro, entrega futura, totais e estado vazio', () => {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '', options: [], hidden: false, children: [], textContent: '',
      add(o) { this.options.push(o); }, replaceChildren(...items) { this.options = []; this.children = items; },
      listeners: {}, append(v) { this.children.push(v); }, addEventListener(tipo, callback) { this.listeners[tipo] = callback; },
    });
    return elements.get(id);
  }
  const row = (componente, quantidade, cfop) => ({ mes_ref: '2026-10', componente, quantidade, cfop, descricao: componente, chave_molde: componente });
  const dados = { producao: { registros: [row('MOLDE COMPLETO',14,'6101'),row('MOLDE COMPLETO',4,'6922'),row('CASTELO',1,'5101'),row('SAPATA',268,'6101'),row('SAPATA',15,'6922')], meses: ['2026-10'], avisos: [], operacao_disponivel: true } };
  const contexto = {
    window: {}, document: { getElementById: element, createElement: () => ({ children: [], append(v) { this.children.push(v); } }) },
    Option: function(text, value) { this.text = text; this.value = value; },
    estado: { dados, charts: {} }, destruirChart() {},
    Chart: function(canvas, config) { this.config = config; },
    formatarAtualizacao: v => v, mesesQualidade: ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],
    Intl, Map, Set, Date, setTimeout,
  };
  vm.createContext(contexto);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'producao.js'), 'utf8'), contexto);
  element('producao-ano').value = '2026'; element('producao-mes').value = '10';
  contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-moldes').textContent, '18');
  assert.equal(element('producao-castelos').textContent, '1');
  assert.equal(element('producao-sapatas').textContent, '283');
  assert.equal(element('producao-vazio').hidden, true);
  element('producao-operacao').value = 'futura'; contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-moldes').textContent, '4');
  assert.equal(element('producao-sapatas').textContent, '15');
  element('producao-componente').value = 'CASTELO'; contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-vazio').hidden, false);
  assert.equal(element('producao-conteudo').hidden, true);
  contexto.window.producaoDashboard.preparar({ registros: [row('CASTELO',1,'')], meses: ['2026-10'], avisos: [], granularidade: 'componente', operacao_disponivel: false });
  assert.equal(element('producao-operacao-grupo').hidden, true);
  assert.equal(element('producao-operacao').value, '');
  contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-castelos').textContent, '1');
  const a = { ...row('CASTELO',2,''), os_molde_completo: '100' };
  const b = { ...row('GRADE',1,''), os_molde_completo: '100' };
  contexto.window.producaoDashboard.preparar({ registros: [a,b], meses: ['2026-10'], avisos: [], formato: 'estrutura_nf', operacao_disponivel: false });
  element('producao-componente').value = '';
  contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-moldes').textContent, '1');
  assert.equal(element('producao-moldes-rotulo').textContent, 'Moldes completos');
  assert.equal(element('producao-castelos').textContent, '2');
  assert.equal(element('producao-castelos-rotulo').textContent, 'Castelos na estrutura');
  const grade = { ...row('GRADE',1,''),nf:'10921',os_principal:'6984',descricao_nf:'MOLD SPM30 MOLDE COMPLETO',molde_id:'10921-6984',classificacao:'COMPONENTE_DE_MOLDE' };
  const sapata = { ...row('SAPATA',15,''),nf:'10921',os_principal:'6984',descricao_nf:'MOLD SPM30 MOLDE COMPLETO',molde_id:'10921-6984',classificacao:'COMPONENTE_DE_MOLDE' };
  const avulso = { ...row('AGITADOR',null,''),nf:'10921',os_principal:'6992',descricao_nf:'AGITADOR 14CM',molde_id:'',classificacao:'COMPONENTE_AVULSO' };
  contexto.window.producaoDashboard.preparar({ registros:[grade,sapata,avulso],moldes:[{id:'10921-6984',nf:'10921',os_principal:'6984',descricao:'MOLD SPM30 MOLDE COMPLETO'}],meses:['2026-10'],avisos:[],formato:'estrutura_nf' });
  element('producao-nf').value = '10921';
  contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-moldes').textContent,'1');
  assert.equal(element('producao-moldes-cards').children.length,1);
  const parent = element('producao-moldes-cards').children[0];
  const grid = parent.children[parent.children.length-1];
  assert.equal(grid.children.length,2);
  assert.equal(element('producao-fora-cards').children.length,1);
  assert.equal(element('producao-sapatas').textContent,'15');
  element('producao-molde').value = '10921-6984';
  contexto.window.producaoDashboard.renderizar();
  assert.equal(element('producao-itens').textContent,'2');
  assert.equal(element('producao-visao-geral').hidden,true);
  assert.equal(element('producao-evolucao').hidden,true);
  assert.equal(element('producao-fora-cards').children[0].children[1].textContent,'OS 6992');
  assert.equal(element('producao-fora-cards').children[0].children[2].textContent,'Quantidade não informada');
});
