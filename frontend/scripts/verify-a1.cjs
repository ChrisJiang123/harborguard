const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

// The compiled verification output is generated and ignored, not application source.
writeFileSync(path.join(__dirname, '../work/verify-a1/package.json'), '{"type":"commonjs"}\n')
const { createMockEngine } = require('../work/verify-a1/data/mock.js')
const { eventIdentity, receiveMessage, useHarbor } = require('../work/verify-a1/store/useHarbor.js')

const messages = []
const engine = createMockEngine(msg => { messages.push(msg); assert.equal(receiveMessage(msg), true) })
engine.start()
assert.equal(useHarbor.getState().latest.buoys.length, 10)
assert.equal(useHarbor.getState().latest.tracks.length, 4)
assert.equal(useHarbor.getState().tracks.T3.cls, 'vessel')
assert.equal(useHarbor.getState().tracks.T4.cls, 'vessel')
assert.equal(useHarbor.getState().latest.zones.length, 10)
assert.equal(useHarbor.getState().latest.alerts.length, 0)

// Simulate exactly the production 200 ms cadence rather than skipping thresholds.
for (let i = 0; i < 450; i++) engine.advance(0.2)
const events = messages.filter(msg => msg.type === 'event')
assert.deepEqual(events.filter(msg => msg.event === 'alert_raised').map(msg => msg.t), [10])
assert.deepEqual(events.filter(msg => msg.event === 'alert_changed').map(msg => [msg.t, msg.data.to_level]), [[35, 2], [60, 3]])
assert.equal(events.find(msg => msg.event === 'detection').t, 35)
assert.equal(events.find(msg => msg.event === 'options_ready').t, 60)
assert.equal(events.find(msg => msg.event === 'recommendation').t, 66)
assert.equal(useHarbor.getState().latest.t, 90)
assert.equal(useHarbor.getState().tracks.T1.depth_m, 12)
assert.equal(useHarbor.getState().tracks.T1.history.length, 60)
assert.equal(useHarbor.getState().latestRec.model, 'template')
assert.equal(useHarbor.getState().optionsByAlert.A1.length, 2)
assert.equal(useHarbor.getState().detections['det-1'].track_id, 'T1')

engine.control('pause')
engine.advance(10)
assert.equal(useHarbor.getState().latest.t, 90)
engine.control('resume')
engine.control('speed', 4)
engine.advance(0.2)
assert.equal(useHarbor.getState().latest.t, 90.8)

useHarbor.getState().selectTrack('T1')
useHarbor.getState().setView('3d')
engine.advance(0.2)
assert.equal(useHarbor.getState().selectedTrackId, 'T1')
useHarbor.getState().setView('2d')
assert.equal(useHarbor.getState().selectedTrackId, 'T1')

engine.decision({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'test' })
assert.deepEqual(useHarbor.getState().latest.zones.filter(zone => zone.state === 'restricted').map(zone => zone.id), ['Z4', 'Z5'])
assert.throws(() => engine.decision({ alert_id: 'missing', option_id: 'opt-1', action: 'approve', operator: 'test' }))

// A hard refresh starts with an empty store; bounded REST history must reconstruct event-derived UI state.
const recoveredSnapshot = useHarbor.getState().latest
const recoveredEvents = messages.filter(msg => msg.type === 'event')
const recoveredLogsNewestFirst = [...useHarbor.getState().logs].reverse()
useHarbor.getState().reset()
useHarbor.getState().recoverLive(recoveredSnapshot, recoveredEvents, recoveredLogsNewestFirst, {}, {})
assert.equal(useHarbor.getState().events.filter(event => event.event === 'decision').length, 1)
assert.equal(useHarbor.getState().decisionsByAlert.A1.action, 'approve')
assert.equal(useHarbor.getState().decisionsByAlert.A1.operator, 'test')
assert.equal(useHarbor.getState().optionsByAlert.A1.length, 2)
assert.equal(useHarbor.getState().detections['det-1'].cls, 'uuv')
assert.equal(useHarbor.getState().latest.seq, recoveredSnapshot.seq)
assert.deepEqual(useHarbor.getState().logs, [...recoveredLogsNewestFirst].reverse())
assert.equal(useHarbor.getState().recovery.phase, 'complete')
useHarbor.getState().recoverLive(recoveredSnapshot, recoveredEvents, recoveredLogsNewestFirst, {}, {})
assert.equal(useHarbor.getState().events.filter(event => event.event === 'decision').length, 1)
const originalRecommendation = recoveredEvents.find(msg => msg.event === 'recommendation')
const replayedRecommendation = { ...originalRecommendation, seq: originalRecommendation.seq + 9000 }
assert.equal(eventIdentity(originalRecommendation), eventIdentity(replayedRecommendation))
receiveMessage(replayedRecommendation)
assert.equal(useHarbor.getState().events.filter(event => event.event === 'recommendation').length, 1)
useHarbor.getState().recoverLive(recoveredSnapshot, recoveredEvents.slice(-500), recoveredLogsNewestFirst, {}, {}, { eventsAvailable: true, eventsReturned: 500, eventLimitReached: true, detailFailures: 0 })
assert.equal(useHarbor.getState().recovery.phase, 'partial')
assert.match(useHarbor.getState().recovery.message, /历史不完整/)
useHarbor.getState().recoverLive(recoveredSnapshot, [], recoveredLogsNewestFirst, {}, {}, { eventsAvailable: false, eventsReturned: 0, eventLimitReached: false, detailFailures: 0 })
assert.equal(useHarbor.getState().recovery.phase, 'failed')
assert.match(useHarbor.getState().recovery.message, /历史加载失败/)
const before = useHarbor.getState().events.length
receiveMessage(events.find(msg => msg.event === 'recommendation'))
assert.equal(useHarbor.getState().events.length, before)
assert.equal(receiveMessage(null), false)
assert.equal(receiveMessage({ type: 'state', seq: 1, t: 1 }), false)
assert.equal(receiveMessage({ type: 'event', seq: 1, t: 1, event: 'log', data: null }), false)

const sessionBeforeServerRestart = useHarbor.getState().session
const restartedSnapshot = { ...recoveredSnapshot, seq: 0, t: 0, tracks: [], alerts: [] }
// WebSocket ingestion applies the new snapshot before async history recovery starts.
useHarbor.setState({ latest: restartedSnapshot })
useHarbor.getState().recoverLive(restartedSnapshot, [], [], {}, {}, { eventsAvailable: true, eventsReturned: 0, eventLimitReached: false, detailFailures: 0, previousSnapshotSeq: recoveredSnapshot.seq })
assert.equal(useHarbor.getState().events.length, 0)
assert.deepEqual(useHarbor.getState().decisionsByAlert, {})
assert.equal(useHarbor.getState().session, sessionBeforeServerRestart + 1)
assert.equal(useHarbor.getState().recovery.phase, 'partial')
assert.match(useHarbor.getState().recovery.message, /序列回退/)

for (let i = 0; i < 650; i++) receiveMessage({ type: 'event', seq: 10000 + i, t: i, event: 'log', data: { log: { t: i, level: 'info', source: 'sim', text: `${i}` } } })
assert.equal(useHarbor.getState().events.length, 500)
assert.equal(useHarbor.getState().logs.length, 200)

useHarbor.getState().reset()
engine.control('reset')
assert.equal(useHarbor.getState().latest.t, 0)
assert.equal(useHarbor.getState().latest.alerts.length, 0)
assert.equal(useHarbor.getState().latestRec, null)
assert.equal(useHarbor.getState().latest.zones.every(zone => zone.state === 'open'), true)
engine.stop()
engine.advance(10)
assert.equal(useHarbor.getState().latest.t, 0)

const staticMessages = []
const staticEngine = createMockEngine(msg => staticMessages.push(msg), [{ id: 'B-real', lat: 33.7, lon: -118.2, range_m: 400 }])
staticEngine.start()
assert.equal(staticMessages[0].buoys[0].id, 'B-real')
assert.equal(staticMessages[0].buoys[0].status, 'ok')

// Exercise the actual WebSocket client with deterministic fake transport/timers.
const ts = require('typescript')
const Module = require('node:module')
const wsPath = path.join(__dirname, '../src/data/ws.ts')
const wsCode = ts.transpileModule(readFileSync(wsPath, 'utf8').replace('import.meta.env.VITE_WS_URL', 'undefined'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText
const wsModule = new Module(wsPath, module)
wsModule.require = name => name === '../store/useHarbor' ? { receiveMessage, useHarbor } : name === './liveRecovery' ? { recoverLiveFromBackend: async () => {} } : require(name)
wsModule._compile(wsCode, wsPath)
const original = { WebSocket: global.WebSocket, setTimeout: global.setTimeout, clearTimeout: global.clearTimeout }
const timers = new Map()
const sockets = []
let timerId = 0
global.setTimeout = (callback, delay) => { timers.set(++timerId, { callback, delay }); return timerId }
global.clearTimeout = id => timers.delete(id)
global.WebSocket = class {
  constructor(url) { this.url = url; sockets.push(this) }
  close() { this.onclose?.() }
}
const runDelay = delay => {
  const pending = [...timers].find(([, timer]) => timer.delay === delay)
  assert.ok(pending, `Expected retry at ${delay}ms`)
  timers.delete(pending[0])
  pending[1].callback()
}
try {
  const stopLive = wsModule.exports.startLive()
  assert.equal(useHarbor.getState().conn, 'connecting')
  sockets.at(-1).onerror()
  assert.equal(useHarbor.getState().conn, 'disconnected')
  runDelay(1000)
  sockets.at(-1).onerror()
  runDelay(2000)
  sockets.at(-1).onerror()
  runDelay(5000)
  sockets.at(-1).onerror()
  runDelay(5000)
  sockets.at(-1).onopen()
  sockets.at(-1).onmessage({ data: JSON.stringify(staticMessages[0]) })
  assert.equal(useHarbor.getState().conn, 'live')
  sockets.at(-1).onmessage({ data: 'malformed json' })
  assert.match(useHarbor.getState().error, /无法解析/)
  stopLive()
  assert.equal(timers.size, 0)
} finally {
  global.WebSocket = original.WebSocket
  global.setTimeout = original.setTimeout
  global.clearTimeout = original.clearTimeout
}

console.log('PASS A0-A1: 200ms cadence; 10/35/60/66s events; pause/resume/speed; selection; mock approval; refresh reconstruction with stable-ID deduplication; explicit complete/partial/failed recovery state; reset; event/log caps; malformed envelopes; WebSocket 1s/2s/5s/5s reconnect; LIVE on valid data; timer cleanup.')
