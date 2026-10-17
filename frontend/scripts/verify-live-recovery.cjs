const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')

const compiled = path.join(__dirname, '../work/verify-recovery')
writeFileSync(path.join(compiled, 'package.json'), '{"type":"commonjs"}\n')
const harbor = require(path.join(compiled, 'store/useHarbor.js'))
const { useHarbor, receiveMessage } = harbor

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

function makeState(seq, alerts = [], tracks = []) {
  return { type: 'state', seq, t: seq, mode: 'security', network: 'online', scenario: 'a', paused: false, speed: 1, buoys: [], tracks, alerts, zones: [] }
}

function event(seq, eventName, data = {}) { return { type: 'event', seq, t: seq, event: eventName, data } }
function log(t, text) { return { t, level: 'info', source: 'sim', text } }
function resetStore(snapshot = makeState(1)) {
  useHarbor.getState().reset()
  useHarbor.getState().setConnection('live')
  assert.equal(receiveMessage(snapshot), true)
}

const apiImpl = {
  events: async () => [],
  logs: async () => [],
  options: async alertId => ({ alert_id: alertId, options: [{ id: 'opt-1', label: 'Baseline' }], ranked: ['opt-1'] }),
  detection: async detectionId => ({ id: detectionId }),
}
const recoveryPath = path.join(__dirname, '../src/data/liveRecovery.ts')
const recoveryModule = new Module(recoveryPath, module)
recoveryModule.require = name => name === './api' ? { api: apiImpl } : name === '../store/useHarbor' ? harbor : require(name)
recoveryModule._compile(ts.transpileModule(readFileSync(recoveryPath, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText, recoveryPath)
const recovery = recoveryModule.exports

async function testRefreshRestoresDecisions() {
  const alert = { id: 'A1', track_id: 'T1', level: 2, risk: .8, breakdown: { C: 0, P: 0, B: 0, Z: 0, D: 0 }, zone_id: null, asset_id: 'X1', distance_m: 10, eta_s: 20, raised_t: 1, updated_t: 10, options_ready: true }
  const snapshot = makeState(30, [alert])
  resetStore(snapshot)
  const optionEvent = event(20, 'options_ready', { alert_id: 'A1', options: [{ id: 'opt-1', label: 'Recovered' }] })
  const decisionEvent = event(21, 'decision', { alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'operator-1' })
  apiImpl.events = async () => [optionEvent, decisionEvent]
  apiImpl.logs = async () => []
  apiImpl.options = async alertId => ({ alert_id: alertId, options: [{ id: 'opt-1', label: 'Recovered' }], ranked: ['opt-1'] })
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  useHarbor.getState().setRecoveryLoading(session)
  await recovery.recoverLiveFromBackend(snapshot, undefined, { generation, session })
  assert.equal(useHarbor.getState().decisionsByAlert.A1.action, 'approve')
  assert.equal(useHarbor.getState().optionsByAlert.A1[0].label, 'Recovered')
  assert.equal(useHarbor.getState().recovery.phase, 'complete')
}

async function testLiveLogsSurviveDelayedHistory() {
  resetStore(makeState(10))
  const historyEvents = deferred(), historyLogs = deferred()
  apiImpl.events = () => historyEvents.promise
  apiImpl.logs = () => historyLogs.promise
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  const request = recovery.recoverLiveFromBackend(makeState(10), undefined, { generation, session, previousSnapshotSeq: 10 })
  const liveLog = log(11, 'new websocket log')
  assert.equal(receiveMessage(event(11, 'log', { log: liveLog })), true)
  historyEvents.resolve([event(4, 'log', { log: log(4, 'older REST log') })])
  historyLogs.resolve([log(4, 'older REST log')]) // Contract v1 returns newest first.
  await request
  assert.deepEqual(useHarbor.getState().logs.map(item => item.text), ['older REST log', 'new websocket log'])
  assert.equal(useHarbor.getState().events.some(item => item.seq === 11), true)
}

async function testStableIdentityPrefersLiveEvent() {
  resetStore(makeState(10))
  const oldRec = { id: 'R1', summary: 'old REST copy' }
  const newRec = { id: 'R1', summary: 'new websocket copy' }
  const liveRecommendation = event(12, 'recommendation', { recommendation: newRec })
  receiveMessage(liveRecommendation)
  apiImpl.events = async () => [event(3, 'recommendation', { recommendation: oldRec })]
  apiImpl.logs = async () => []
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  await recovery.recoverLiveFromBackend(makeState(10), undefined, { generation, session })
  assert.equal(useHarbor.getState().events.filter(item => item.event === 'recommendation').length, 1)
  assert.equal(useHarbor.getState().latestRec.summary, 'new websocket copy')
  receiveMessage(event(99, 'recommendation', { recommendation: oldRec }))
  assert.equal(useHarbor.getState().events.filter(item => item.event === 'recommendation').length, 1)
}

async function testOrdinaryDelayDoesNotLookLikeRestart() {
  resetStore(makeState(50))
  const historyEvents = deferred(), historyLogs = deferred()
  apiImpl.events = () => historyEvents.promise
  apiImpl.logs = () => historyLogs.promise
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  const request = recovery.recoverLiveFromBackend(makeState(50), undefined, { generation, session, previousSnapshotSeq: 50 })
  receiveMessage(makeState(75))
  historyEvents.resolve([])
  historyLogs.resolve([])
  await request
  assert.equal(useHarbor.getState().latest.seq, 75)
  assert.equal(useHarbor.getState().recovery.phase, 'complete')
  assert.doesNotMatch(useHarbor.getState().recovery.message ?? '', /restart|sequence reset/)
}

async function testBackendRestartUsesConnectionBaseline() {
  const approved = event(90, 'decision', { alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'operator-1' })
  resetStore(makeState(100))
  receiveMessage(approved)
  const oldSession = useHarbor.getState().session
  // Mirrors ws.ts: the first lower-sequence snapshot clears the old session before ingest.
  useHarbor.getState().reset()
  receiveMessage(makeState(0))
  apiImpl.events = async () => []
  apiImpl.logs = async () => []
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  await recovery.recoverLiveFromBackend(makeState(0), undefined, { generation, session, previousSnapshotSeq: 100 })
  assert.deepEqual(useHarbor.getState().decisionsByAlert, {})
  assert.equal(useHarbor.getState().session, oldSession + 1)
  assert.equal(useHarbor.getState().recovery.phase, 'partial')
  assert.match(useHarbor.getState().recovery.message, /pre-restart/)
}

async function testResetAndNewSocketInvalidateLateResponses() {
  resetStore(makeState(20))
  const historyEvents = deferred(), historyLogs = deferred()
  apiImpl.events = () => historyEvents.promise
  apiImpl.logs = () => historyLogs.promise
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  const request = recovery.recoverLiveFromBackend(makeState(20), undefined, { generation, session })
  useHarbor.getState().reset()
  receiveMessage(makeState(2))
  historyEvents.resolve([event(19, 'decision', { alert_id: 'old', option_id: 'x', action: 'approve', operator: 'old-session' })])
  historyLogs.resolve([log(19, 'old session')])
  await request
  assert.equal(useHarbor.getState().events.length, 0)
  assert.equal(useHarbor.getState().logs.length, 0)
  assert.equal(useHarbor.getState().recovery.phase, 'idle')

  const lateEvents = deferred(), lateLogs = deferred()
  apiImpl.events = () => lateEvents.promise
  apiImpl.logs = () => lateLogs.promise
  const oldGeneration = recovery.beginLiveRecoveryGeneration()
  const newSession = useHarbor.getState().session
  const secondRequest = recovery.recoverLiveFromBackend(makeState(2), undefined, { generation: oldGeneration, session: newSession })
  recovery.beginLiveRecoveryGeneration() // A reconnect owns recovery now.
  lateEvents.resolve([event(3, 'decision', { alert_id: 'stale', option_id: 'x', action: 'approve', operator: 'stale' })])
  lateLogs.resolve([])
  await secondRequest
  assert.equal(useHarbor.getState().events.length, 0)

  const scenarioEvents = deferred(), scenarioLogs = deferred()
  apiImpl.events = () => scenarioEvents.promise
  apiImpl.logs = () => scenarioLogs.promise
  const scenarioGeneration = recovery.beginLiveRecoveryGeneration()
  const scenarioSession = useHarbor.getState().session
  const scenarioRequest = recovery.recoverLiveFromBackend(makeState(2), undefined, { generation: scenarioGeneration, session: scenarioSession })
  receiveMessage(event(4, 'scenario_changed', { scenario: 'b', status: 'started' }))
  scenarioEvents.resolve([event(3, 'decision', { alert_id: 'stale', option_id: 'x', action: 'approve', operator: 'stale' })])
  scenarioLogs.resolve([])
  await scenarioRequest
  assert.equal(useHarbor.getState().session, scenarioSession + 1)
  assert.equal(useHarbor.getState().decisionsByAlert.stale, undefined)
}

async function testHistoryCapIsExplicitlyPartial() {
  resetStore(makeState(600))
  apiImpl.events = async () => Array.from({ length: 500 }, (_, index) => event(index + 1, 'other'))
  apiImpl.logs = async () => []
  const generation = recovery.beginLiveRecoveryGeneration()
  const session = useHarbor.getState().session
  await recovery.recoverLiveFromBackend(makeState(600), undefined, { generation, session })
  assert.equal(useHarbor.getState().recovery.phase, 'partial')
  assert.match(useHarbor.getState().recovery.message, /Incomplete history/)
  assert.equal(useHarbor.getState().events.length, 500)
}

function testSocketCapturesSequenceBeforeAsyncRestore() {
  const wsPath = path.join(__dirname, '../src/data/ws.ts')
  const source = readFileSync(wsPath, 'utf8').replace('import.meta.env.VITE_WS_URL', 'undefined')
  const wsCode = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText
  const wsModule = new Module(wsPath, module)
  const sockets = [], timers = new Map(), contexts = []
  let timerId = 0, generation = 0
  const originals = { WebSocket: global.WebSocket, setTimeout: global.setTimeout, clearTimeout: global.clearTimeout }
  const recoveryMock = {
    beginLiveRecoveryGeneration: () => ++generation,
    invalidateLiveRecoveryGeneration: value => { if (value === generation) generation++ },
    recoverLiveFromBackend: (_snapshot, _signal, context) => { contexts.push(context) },
  }
  wsModule.require = name => name === '../store/useHarbor' ? harbor : name === './liveRecovery' ? recoveryMock : require(name)
  wsModule._compile(wsCode, wsPath)
  global.setTimeout = (callback, delay) => { timers.set(++timerId, { callback, delay }); return timerId }
  global.clearTimeout = id => timers.delete(id)
  global.WebSocket = class { constructor() { sockets.push(this) } close() { this.onclose?.() } }
  try {
    useHarbor.setState({ latest: makeState(50) })
    const baselineSession = useHarbor.getState().session
    const stop = wsModule.exports.startLive()
    useHarbor.setState({ latest: makeState(150) })
    sockets[0].onmessage({ data: JSON.stringify(makeState(60)) })
    assert.equal(contexts[0].previousSnapshotSeq, 50)
    assert.equal(contexts[0].session, useHarbor.getState().session)
    assert.equal(useHarbor.getState().session, baselineSession)
    sockets[0].onclose()
    assert.equal(timers.size, 1)
    const [retryId, retryTimer] = [...timers.entries()][0]
    timers.delete(retryId)
    retryTimer.callback()
    sockets[0].onmessage({ data: JSON.stringify(event(61, 'log', { log: log(61, 'message from superseded socket') })) })
    assert.equal(useHarbor.getState().logs.some(item => item.text === 'message from superseded socket'), false)
    const beforeRestart = useHarbor.getState().session
    sockets[1].onmessage({ data: JSON.stringify(makeState(0)) })
    assert.equal(contexts.length, 2)
    assert.ok(contexts[1].generation > contexts[0].generation)
    assert.equal(contexts[1].previousSnapshotSeq, 60)
    assert.equal(useHarbor.getState().session, beforeRestart + 1)
    stop()
  } finally {
    global.WebSocket = originals.WebSocket
    global.setTimeout = originals.setTimeout
    global.clearTimeout = originals.clearTimeout
  }
}

async function main() {
  await testRefreshRestoresDecisions()
  await testLiveLogsSurviveDelayedHistory()
  await testStableIdentityPrefersLiveEvent()
  await testOrdinaryDelayDoesNotLookLikeRestart()
  await testBackendRestartUsesConnectionBaseline()
  await testResetAndNewSocketInvalidateLateResponses()
  await testHistoryCapIsExplicitlyPartial()
  testSocketCapturesSequenceBeforeAsyncRestore()
  console.log('PASS live recovery races: REST/WebSocket log merge, refresh decisions, stable-ID dedupe, reconnect-start sequence baseline, backend restart, reset/scenario/generation invalidation, and explicit 500-event partial history.')
}

main().catch(error => { console.error(error); process.exitCode = 1 })
