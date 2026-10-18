// Exercise the real API wrapper with a public deployment origin; no network/model calls.
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')
const base = 'https://harborguard-backend.invalid/api'
const calls = []
class APIError extends Error {}
const source = readFileSync(path.join(__dirname, '../src/data/api.ts'), 'utf8')
  .replaceAll('import.meta.env.VITE_API_BASE', JSON.stringify(base + '/'))
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 },
}).outputText
const mod = new Module(__filename, module)
mod.require = name => {
  if (name === '../store/useHarbor') return { useHarbor: { getState: () => ({ conn: 'live' }) } }
  if (name === './http') return { APIError, requestJSON: async (...args) => { calls.push(args); return {} } }
  if (name === './mock') return { getMock: () => { throw new Error('Live request must not use a mock') } }
  if (name === './staticData') return { loadLocalData: () => { throw new Error('Live request must not use local data') } }
  throw new Error(`Unexpected runtime dependency: ${name}`)
}
mod._compile(compiled, __filename)
async function main() {
  const { api } = mod.exports
  await api.metrics()
  await api.ask('Which evidence supports this recommendation?', 'T1')
  assert.equal(calls[0][0], base + '/metrics')
  assert.equal(calls[1][0], base + '/agent/ask')
  assert.equal(calls[1][1].method, 'POST')
  assert.deepEqual(JSON.parse(calls[1][1].body), { question: 'Which evidence supports this recommendation?', track_id: 'T1' })
  assert.equal(calls[1][2], 19000)
  assert.equal(api.sonarURL('det/a b'), base + '/sonar/det%2Fa%20b.png')
  assert.ok(calls.every(([url]) => url.startsWith(base + '/')))
  console.log('PASS public API configuration: metrics, Agent ask (19s budget), encoded sonar URL; no network/model calls.')
}
main().catch(error => { console.error(error); process.exitCode = 1 })
