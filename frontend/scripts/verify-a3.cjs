const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')
writeFileSync(path.join(__dirname, '../work/verify-a3/package.json'), '{"type":"commonjs"}\n')
const root = path.join(__dirname, '../work/verify-a3')
const { useHarbor, receiveMessage } = require(path.join(root, 'store/useHarbor.js'))
const { runOperation, useOperations } = require(path.join(root, 'store/useOperations.js'))
const { createMockEngine, startMock, getMock } = require(path.join(root, 'data/mock.js'))
const { loadLocalData } = require(path.join(root, 'data/staticData.js'))
const { activeAlertId, effectiveOptionId, riskContributions } = require(path.join(root, 'panels/selection.js'))
const { zoneStyle } = require(path.join(root, 'map2d/styles.js'))
const { requestJSON, APIError } = require(path.join(root, 'data/http.js'))

const apiPath = path.join(__dirname, '../src/data/api.ts')
const apiCode = ts.transpileModule(readFileSync(apiPath, 'utf8').replace('import.meta.env.VITE_API_BASE', 'undefined'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText
const apiModule = new Module(apiPath, module)
apiModule.require = name => name.startsWith('../store/') ? require(path.join(root, 'store', name.slice('../store/'.length) + '.js')) : name.startsWith('./') ? require(path.join(root, 'data', name.slice(2) + '.js')) : require(name)
apiModule._compile(apiCode, apiPath)
const { api } = apiModule.exports

function seedLive() {
  useHarbor.getState().reset()
  const engine = createMockEngine(msg => receiveMessage(msg))
  engine.start()
  for (let i = 0; i < 330; i++) engine.advance(.2)
  engine.control('pause')
  useHarbor.getState().setConnection('live')
  return engine
}

async function main() {
  const originalFetch = global.fetch
  let stop
  const calls = []
  try {
    // Static files are stubbed too; none of these tests contacts a browser, OSM, or a backend.
    global.fetch = async (url, init) => { calls.push([url, init]); return new Response('', { status: 404 }) }
    stop = startMock()
    await loadLocalData()
    const engine = getMock()
    assert.ok(engine)
    await api.startScenario('a', 10)
    engine.advance(6.6)
    await api.control({ action: 'pause' })
    let state = useHarbor.getState()
    assert.equal(state.latest.t, 66)
    assert.equal(state.latest.speed, 10)
    assert.equal(state.latest.paused, true)
    assert.equal(activeAlertId(state), 'A1')
    const rec = state.recByAlert.A1
    const options = state.optionsByAlert.A1
    assert.equal(effectiveOptionId('A1', options, rec, null, null), 'opt-1')
    assert.equal(effectiveOptionId('A1', options, rec, 'port-closure', 'A2'), 'opt-1')
    assert.equal(effectiveOptionId('A1', options, rec, 'missing', 'A1'), null)
    assert.equal(effectiveOptionId(null, options, rec, 'opt-1', 'A1'), null)
    const risk = state.alerts.A1.risk
    const parts = riskContributions(state.alerts.A1)
    assert.deepEqual(parts.map(part => part.key), ['C', 'P', 'B', 'Z', 'D'])
    assert.ok(Math.abs(parts.reduce((sum, part) => sum + part.weighted, 0) - risk) < .01)
    assert.equal(state.alerts.A1.risk, risk)
    state.selectTrack('T2')
    assert.equal(activeAlertId(useHarbor.getState()), null)
    state.selectTrack('T1')
    state.chooseOption('A1', 'port-closure')
    assert.equal(effectiveOptionId('A1', options, rec, useHarbor.getState().chosenOptionId, useHarbor.getState().chosenOptionAlertId), 'port-closure')
    assert.equal(zoneStyle('open', true).dashArray, '8 5')
    assert.equal(zoneStyle('open', false, true).color, '#7dd3fc')

    const localCalls = calls.length
    await api.decide({ alert_id: 'A1', option_id: 'port-closure', action: 'approve', operator: 'Operator A' })
    state = useHarbor.getState()
    assert.equal(state.decisionsByAlert.A1.action, 'approve')
    assert.equal(state.decisionsByAlert.A1.option_id, 'port-closure')
    assert.equal(state.decisionsByAlert.A1.t, 66)
    assert.equal(state.decisionRequests.A1, undefined)
    assert.equal(state.latest.zones.filter(zone => zone.state === 'restricted').length, 10)
    await assert.rejects(() => api.decide({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'A' }), /already been handled/)
    assert.equal(calls.length, localCalls)

    await api.startScenario('a', 10)
    engine.advance(6.6)
    await api.control({ action: 'pause' })
    assert.equal(useHarbor.getState().decisionsByAlert.A1, undefined)
    await api.decide({ alert_id: 'A1', option_id: 'opt-1', action: 'reject', operator: 'A' })
    assert.equal(useHarbor.getState().decisionsByAlert.A1.action, 'reject')
    assert.equal(useHarbor.getState().latest.zones.every(zone => zone.state === 'open'), true)
    await api.inject({ type: 'network_down' })
    assert.equal(useHarbor.getState().latest.network, 'offline')
    assert.equal(useHarbor.getState().recByAlert.A1.model, 'template')
    await api.inject({ type: 'network_up' })
    assert.equal(useHarbor.getState().latest.network, 'online')
    await api.inject({ type: 'buoy_down', target: 'B1' })
    assert.equal(useHarbor.getState().latest.buoys[0].status, 'down')
    await api.mode('disaster')
    assert.equal(useHarbor.getState().latest.mode, 'disaster')
    assert.equal(Object.keys(useHarbor.getState().alerts).length, 0)
    await api.startScenario('b')
    assert.equal(useHarbor.getState().latest.scenario, 'b')
    assert.equal(useHarbor.getState().latest.mode, 'disaster')
    await api.control({ action: 'reset' })
    state = useHarbor.getState()
    assert.equal(state.latest.t, 0)
    assert.equal(state.latest.scenario, null)
    assert.equal(state.latest.paused, true)
    assert.deepEqual(state.decisionsByAlert, {})
    assert.deepEqual(state.decisionRequests, {})
    assert.equal(state.chosenOptionId, null)

    state.setConnection('replay')
    await assert.rejects(() => api.startScenario('a'), /disabled during replay/)
    state.setConnection('disconnected')
    await assert.rejects(() => api.control({ action: 'resume' }), /disconnected/)
    assert.equal(calls.length, localCalls)
    stop(); stop = null

    seedLive()
    const postCalls = []
    global.fetch = async (url, init) => { postCalls.push({ url, init }); return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } }) }
    const input = { alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'Operator A' }
    await api.decide(input)
    assert.equal(useHarbor.getState().decisionsByAlert.A1, undefined)
    assert.ok(useHarbor.getState().decisionRequests.A1)
    assert.equal(postCalls.length, 1)
    assert.equal(postCalls[0].url, 'http://localhost:8000/api/decision')
    assert.deepEqual(JSON.parse(postCalls[0].init.body), input)
    receiveMessage({ type: 'event', seq: 100000, t: 67, event: 'decision', data: input })
    assert.equal(useHarbor.getState().decisionsByAlert.A1.t, 67)
    assert.equal(useHarbor.getState().decisionRequests.A1, undefined)
    assert.equal(useHarbor.getState().latest.zones.every(zone => zone.state === 'open'), true)
    receiveMessage({ type: 'event', seq: 100001, t: 67, event: 'zone_changed', data: { zone_id: 'Z4', state: 'restricted' } })
    assert.equal(useHarbor.getState().latest.zones.find(zone => zone.id === 'Z4').state, 'restricted')

    seedLive()
    const rejectInput = { ...input, action: 'reject' }
    await api.decide(rejectInput)
    assert.equal(useHarbor.getState().decisionRequests.A1, undefined)
    assert.equal(useHarbor.getState().decisionsByAlert.A1, undefined)
    assert.equal(useHarbor.getState().uncertainDecisions.A1.reason, 'reject-without-event')
    receiveMessage({ type: 'event', seq: 100002, t: 68, event: 'decision', data: rejectInput })
    assert.equal(useHarbor.getState().uncertainDecisions.A1, undefined)
    assert.equal(useHarbor.getState().decisionsByAlert.A1.action, 'reject')

    seedLive()
    global.fetch = async () => new Response(JSON.stringify({ detail: 'Option not found' }), { status: 422, headers: { 'content-type': 'application/json' } })
    const success = await runOperation('Approve option', () => api.decide(input))
    assert.equal(success, false)
    assert.equal(useOperations.getState().pending, null)
    assert.match(useOperations.getState().toast.text, /Option not found/)
    assert.equal(useOperations.getState().toast.kind, 'error')
    assert.equal(useHarbor.getState().decisionsByAlert.A1, undefined)
    assert.equal(useHarbor.getState().decisionRequests.A1, undefined)

    global.fetch = async () => new Response(JSON.stringify({ ok: false }), { headers: { 'content-type': 'application/json' } })
    await assert.rejects(() => api.startScenario('a'), /did not confirm/)
    global.fetch = async () => { throw new TypeError('offline') }
    await assert.rejects(() => api.control({ action: 'pause' }), /Connection failed/)
    global.fetch = async () => new Response('not json', { headers: { 'content-type': 'text/plain' } })
    await assert.rejects(() => requestJSON('https://example.invalid/'), error => error instanceof APIError && /valid JSON/.test(error.message))

    let release
    let duplicate = false
    const first = runOperation('Test action', () => new Promise(resolve => { release = resolve }))
    assert.equal(useOperations.getState().pending, 'Test action')
    assert.equal(await runOperation('Duplicate action', async () => { duplicate = true }), false)
    assert.equal(duplicate, false)
    release()
    assert.equal(await first, true)
    assert.equal(useOperations.getState().pending, null)

    const previousSession = useHarbor.getState().session
    receiveMessage({ type: 'event', seq: 200000, t: 0, event: 'scenario_changed', data: { scenario: 'a', status: 'started' } })
    assert.equal(useHarbor.getState().session, previousSession + 1)
    assert.deepEqual(useHarbor.getState().decisionRequests, {})
    assert.deepEqual(useHarbor.getState().optionsByAlert, {})
    assert.equal(useHarbor.getState().latestRec, null)
    console.log('PASS A3: scenario A approval/rejection; manual/default options; target-specific context; contribution display; network/mode/scenario controls; replay POST lock; real-event-only confirmation; explicit unconfirmed reject state; HTTP/toast errors; request de-duplication; clean session reset.')
  } finally {
    stop?.()
    global.fetch = originalFetch
    useOperations.setState({ pending: null })
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
