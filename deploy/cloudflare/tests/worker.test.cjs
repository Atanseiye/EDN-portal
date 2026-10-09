const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

// Exercise the Worker adapter without starting or billing a cloud container.
function load() {
  const source = fs.readFileSync(`${__dirname}/../src/index.ts`, 'utf8');
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText;
  const calls = [];
  const context = {
    exports: {}, URL, Request, Response, Headers,
    require: () => ({
      Container: class { constructor() {} },
      getContainer: (binding, name) => {
        calls.push({ binding, name });
        return { fetch: async request => { calls.push(request); return new Response('ok'); } };
      }
    })
  };
  vm.runInNewContext(code, context);
  return { ...context.exports, calls };
}

test('secrets reach container environment and insecure storage is rejected', () => {
  const { EDNAiContainer } = load();
  const config = {
    APP_ENV: 'production',
    EDNAI_DATABASE_URL: 'postgresql://test:test@example.com/db?sslmode=require',
    EDNAI_ADMIN_TOKEN: 'test-only-secret'
  };
  const create = values => new EDNAiContainer({}, { EDNAI_CONFIG: JSON.stringify(values) });
  assert.equal(create(config).envVars.EDNAI_ADMIN_TOKEN, config.EDNAI_ADMIN_TOKEN);
  assert.throws(() => create({ ...config, EDNAI_DATABASE_URL: 'postgresql://example.com/db' }), /TLS/);
  assert.throws(() => create({ ...config, EDNAI_DATABASE_URL: 'sqlite:///tmp/db' }), /PostgreSQL/);
  assert.throws(() => create({ ...config, APP_ENV: 'development' }), /production/);
  assert.throws(() => create({ ...config, PATH: '/tmp/untrusted' }), /unsupported/);
});

test('uses a stable instance and replaces spoofed forwarding headers', async () => {
  const worker = load();
  const request = new Request('https://ednai.example.com/v1/models', {
    headers: { 'cf-connecting-ip': '192.0.2.10', 'x-forwarded-for': 'spoofed', cookie: 'session=test' }
  });
  const response = await worker.default.fetch(request, { EDNAI_CONTAINER: 'binding' });
  assert.equal(worker.calls[0].name, 'ednai-primary');
  assert.equal(worker.calls[1].headers.get('x-forwarded-for'), '192.0.2.10');
  assert.equal(worker.calls[1].headers.get('x-forwarded-proto'), 'https');
  assert.equal(worker.calls[1].headers.get('cookie'), 'session=test');
  assert.equal(worker.calls[1].url, request.url);
  assert.equal(await response.text(), 'ok');
});
