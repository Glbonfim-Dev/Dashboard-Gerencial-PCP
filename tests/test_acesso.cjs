// Executar: node --test tests/test_acesso.cjs (sem dependências adicionais).
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '..', 'acesso.js'), 'utf8');
const ENTRY = 'dashboard-identificacao-v1';
const LOG = 'dashboard-acessos-v1';

function storage(initial = {}, fail = () => false) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem(key) { if (fail('get', key)) throw Error('Blocked'); return data.get(key) ?? null; },
    setItem(key, value) { if (fail('set', key)) throw Error('Blocked'); data.set(key, String(value)); },
    removeItem(key) { if (fail('remove', key)) throw Error('Blocked'); data.delete(key); }
  };
}

function browser({ login = true, local = storage(), session = storage(), hash = '' } = {}) {
  const events = {}, targets = [];
  const input = { value: '', focus() { this.focused = true; } };
  const remember = { checked: false }, error = { hidden: true };
  const form = { addEventListener(name, fn) { events[name] = fn; } };
  const logout = { addEventListener(name, fn) { events.logout = fn; } };
  const elements = { '#login-form': login ? form : null, '#usuario': input,
    '#manter-conectado': remember, '#login-error': error, '#sair-dashboard': logout };
  const context = {
    URL, Date, localStorage: local, sessionStorage: session,
    location: { hash, pathname: '/dashboard/index.html', search: '',
      replace(url) { targets.push(url); }, assign(url) { targets.push(url); } },
    history: { replaceState() {} },
    document: { baseURI: 'https://empresa.test/dashboard/' + (login ? 'login.html' : 'index.html'),
      querySelector(id) { return elements[id] ?? null; }, documentElement: { classList: { remove() {} } } },
    addEventListener(name, fn) { events[name] = fn; }
  };
  context.window = context;
  vm.runInNewContext(source, context);
  return { context, input, remember, error, events, targets, local, session,
    submit(name, keep = false) {
      input.value = name; remember.checked = keep;
      events.submit({ preventDefault() {} });
    } };
}

test('sem identificação abre a entrada no mesmo subdiretório', () => {
  const page = browser({ login: false });
  assert.equal(page.context.dashboardAccessGranted, false);
  assert.deepEqual(page.targets, ['https://empresa.test/dashboard/login.html']);
});

test('identifica, registra somente usuário/data/hora e usa sessão da aba', () => {
  const page = browser(); page.submit('  Teste Corporativo  ');
  const record = JSON.parse(page.local.getItem(LOG))[0];
  assert.deepEqual(Object.keys(record).sort(), ['data', 'hora', 'usuario']);
  assert.equal(record.usuario, 'Teste Corporativo');
  assert(record.data && record.hora);
  assert.equal(page.local.getItem(ENTRY), null);
  assert.equal(JSON.parse(page.session.getItem(ENTRY)).usuario, 'Teste Corporativo');
  assert.equal(page.targets.at(-1), 'https://empresa.test/dashboard/index.html');
});

test('manter conectado persiste entre visitas, sem solicitar credenciais', () => {
  const page = browser(); page.submit('teste.corporativo', true);
  assert.equal(page.session.getItem(ENTRY), null);
  const saved = JSON.parse(page.local.getItem(ENTRY));
  assert(saved.expiraEm > Date.now() + 29 * 86400000);
  const visit = browser({ local: page.local });
  assert.equal(visit.targets.at(-1), 'https://empresa.test/dashboard/index.html');
  assert.equal(JSON.parse(page.local.getItem(LOG)).length, 1);
});

test('nomes vazios ou caracteres de controle são rejeitados', () => {
  for (const name of ['  ', 'a', 'Teste\nOutro']) {
    const page = browser(); page.submit(name);
    assert.equal(page.targets.length, 0); assert.equal(page.error.hidden, false);
    assert.equal(page.local.getItem(LOG), null);
  }
});

test('identificação expirada ou armazenamento corrompido volta à entrada', () => {
  for (const value of [JSON.stringify({ usuario: 'Teste', expiraEm: 1 }), '{invalid']) {
    const page = browser({ login: false, local: storage({ [ENTRY]: value }) });
    assert.equal(page.context.dashboardAccessGranted, false);
    assert(page.targets[0].endsWith('/login.html'));
  }
});

test('sair limpa as identificações e preserva o histórico', () => {
  const page = browser(); page.submit('Teste', true);
  const visit = browser({ login: false, local: page.local, session: page.session });
  assert.equal(visit.context.dashboardAccessGranted, true);
  visit.events.logout();
  assert.equal(page.local.getItem(ENTRY), null); assert.equal(page.session.getItem(ENTRY), null);
  assert.equal(JSON.parse(page.local.getItem(LOG)).length, 1);
  assert(visit.targets.at(-1).endsWith('/login.html'));
});

test('falha no registro não impede abrir o dashboard', () => {
  const page = browser({ local: storage({}, (action, key) => action === 'set' && key === LOG) });
  page.submit('Teste');
  assert(page.targets.at(-1).endsWith('/index.html'));
  assert(page.session.getItem(ENTRY));
});

test('armazenamento persistente bloqueado usa a sessão como alternativa', () => {
  const page = browser({ local: storage({}, () => true) }); page.submit('Teste', true);
  assert(page.session.getItem(ENTRY)); assert(page.targets.at(-1).endsWith('/index.html'));
});

test('sem armazenamento permite uma entrada sem persistência', () => {
  const page = browser({ local: storage({}, () => true), session: storage({}, () => true) });
  page.submit('Teste');
  assert(page.targets.at(-1).endsWith('#entrada-sem-persistencia'));
  const dashboard = browser({ login: false, hash: '#entrada-sem-persistencia',
    local: page.local, session: page.session });
  assert.equal(dashboard.context.dashboardAccessGranted, true);
});

test('histórico mantém somente os últimos cem registros', () => {
  const records = Array.from({ length: 100 }, (_, i) => ({ usuario: 'Teste ' + i, data: '01/01/2026', hora: '12:00:00' }));
  const page = browser({ local: storage({ [LOG]: JSON.stringify(records) }) });
  page.submit('Nova entrada');
  const saved = JSON.parse(page.local.getItem(LOG));
  assert.equal(saved.length, 100); assert.equal(saved[0].usuario, 'Teste 1');
  assert.equal(saved.at(-1).usuario, 'Nova entrada');
});
