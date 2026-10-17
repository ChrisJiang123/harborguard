const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const Module = require('node:module')
const ts = require('typescript')
const root = path.join(__dirname, '../work/verify-a5')
writeFileSync(path.join(root, 'package.json'), '{"type":"commonjs"}\n')
const { createMockEngine, startMock, getMock } = require(path.join(root, 'data/mock.js'))
const { useHarbor, receiveMessage } = require(path.join(root, 'store/useHarbor.js'))
const { useReplay } = require(path.join(root, 'store/useReplay.js'))
const { startReplay } = require(path.join(root, 'data/replay.js'))
const { parseReplay, replayPath, rebuildReplay, createReplayClock } = require(path.join(root, 'data/replayCore.js'))
const { localSonarPath, metricEntries } = require(path.join(root, 'data/presentation.js'))
const { parseLocalBase, loadLocalBase } = require(path.join(root, 'data/localBase.js'))
const { loadLocalData } = require(path.join(root, 'data/staticData.js'))
const apiPath = path.join(__dirname, '../src/data/api.ts')
const apiModule = new Module(apiPath, module)
apiModule.require = name => name.startsWith('../store/') ? require(path.join(root, 'store', name.slice(9) + '.js')) : name.startsWith('./') ? require(path.join(root, 'data', name.slice(2) + '.js')) : require(name)
apiModule._compile(ts.transpileModule(readFileSync(apiPath, 'utf8').replace('import.meta.env.VITE_API_BASE', 'undefined'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText, apiPath)
const { api } = apiModule.exports

function recordScenario(scenario) {
  const rows = []
  const engine = createMockEngine(msg => rows.push({ wall_ms: msg.t * 1000, msg }))
  engine.startScenario(scenario)
  for (let i = 1; i <= 450; i++) {
    engine.advance(.2)
    if (i === 150) engine.inject({ type: 'buoy_down', target: 'B1' })
    if (i === 250) engine.inject({ type: 'network_down' })
    if (scenario === 'a' && i === 350) engine.decision({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'Test Recording' })
  }
  return { rows, engine }
}
const dataOnly = state => {
  const { latest, tracks, alerts, events, logs, optionsByAlert, recByAlert, latestRec, detections, reopenPlan, decisionsByAlert, decisionRequests } = state
  return { latest, tracks, alerts, events, logs, optionsByAlert, recByAlert, latestRec, detections, reopenPlan, decisionsByAlert, decisionRequests }
}

async function main() {
  const originalFetch = global.fetch
  let cleanup
  try {
    const { rows: a } = recordScenario('a')
    const { rows: b } = recordScenario('b')
    assert.deepEqual(parseReplay('\uFEFF' + a.map(JSON.stringify).join('\r\n')), a)
    assert.equal(replayPath('data/replay_a.jsonl'), '/data/replay_a.jsonl')
    for (const file of ['../x.jsonl', '/x.jsonl', 'https://example.com/a.jsonl', 'a.jsonl?x=1', 'a.txt']) assert.throws(() => replayPath(file))
    for (const text of ['', 'not json', '{}', 'null', '{"wall_ms":0,"msg":{}}', JSON.stringify({ wall_ms: 0, msg: { type: 'event', seq: 1, t: 0, event: 'log', data: {} } })]) assert.throws(() => parseReplay(text))
    assert.throws(() => parseReplay([JSON.stringify({ ...a[0], wall_ms: 2 }), JSON.stringify({ ...a[1], wall_ms: 1 })].join('\n')), /out-of-order/)
    assert.throws(() => parseReplay(JSON.stringify({ ...a[0], wall_ms: -1 })))

    useHarbor.getState().reset()
    useHarbor.getState().setView('3d')
    useHarbor.setState(rebuildReplay(a, a.length, useHarbor.getState()))
    let state = useHarbor.getState()
    assert.equal(state.conn, 'replay')
    assert.equal(state.view, '3d')
    assert.equal(state.decisionsByAlert.A1.action, 'approve')
    assert.equal(state.detections['det-1'].model, 'stub')
    assert.equal(state.latest.network, 'offline')
    assert.equal(state.latest.buoys[0].status, 'down')
    assert.equal(state.latest.zones.filter(zone => zone.state === 'restricted').length, 2)

    for (const rows of [a, b]) {
      for (const time of [0, 10000, 23900, 24000, 35000, 44900, 45000, 66000, 70000, 90000, 12000, 0]) {
        const end = rows.filter(row => row.wall_ms <= time).length
        const rebuilt = rebuildReplay(rows, end, useHarbor.getState())
        useHarbor.getState().reset()
        for (const row of rows.slice(0, end)) receiveMessage(row.msg)
        assert.deepEqual(dataOnly(rebuilt), dataOnly(useHarbor.getState()), `seek ${rows === a ? 'A' : 'B'} ${time}`)
      }
    }
    state = rebuildReplay(b, b.filter(row => row.wall_ms <= 45000).length, useHarbor.getState())
    assert.equal(state.reopenPlan.est_hours_saved, 9)
    assert.deepEqual(state.reopenPlan.route_zone_ids, ['Z1', 'Z2'])
    assert.equal(state.latest.zones.filter(zone => zone.state === 'clear').length, 6)
    assert.equal(state.latest.zones.filter(zone => zone.state === 'blocked').length, 1)
    assert.equal(state.latest.zones.filter(zone => zone.state === 'unsurveyed').length, 3)
    assert.equal(state.latestRec.model, 'template')
    assert.deepEqual(state.detections, {})
    assert.deepEqual(state.optionsByAlert, {})
    assert.deepEqual(state.decisionsByAlert, {})

    // Wall-time playback must not use msg.t: a recording may change speed/reset sim time.
    const mixed = [...a.slice(0, 5), ...b.slice(0, 8)].map((row, i) => ({ ...row, wall_ms: 500 + i * 100 }))
    let emitted = [], lastEnd = 0
    const clock = createReplayClock(mixed, row => emitted.push(row), end => { lastEnd = end })
    assert.equal(lastEnd, 1)
    clock.play(true); clock.tick(150)
    assert.equal(clock.status().position, 150)
    assert.equal(emitted.length, 1)
    clock.play(false); clock.tick(5000)
    assert.equal(clock.status().position, 150)
    clock.setSpeed(2); clock.play(true); clock.tick(100)
    assert.equal(clock.status().position, 350)
    clock.setSpeed(10); assert.equal(clock.status().speed, 2)
    clock.seek(250); assert.equal(lastEnd, 3)
    clock.tick(100000); assert.equal(clock.status().playing, false)
    assert.equal(clock.status().position, clock.status().duration)
    clock.play(true); assert.equal(clock.status().position, 0)
    clock.seek(-100); assert.equal(clock.status().position, 0)
    clock.seek(NaN); assert.equal(clock.status().position, 0)

    // A scenario reset inside one recording removes the previous event-derived caches.
    const lastSeq = Math.max(...a.map(row => row.msg.seq))
    const joined = [...a, ...b.map(row => ({ ...row, wall_ms: row.wall_ms + 91000, msg: { ...row.msg, seq: row.msg.seq + lastSeq } }))]
    assert.doesNotThrow(() => parseReplay(joined.map(JSON.stringify).join('\n')))
    state = rebuildReplay(joined, joined.length, useHarbor.getState())
    assert.deepEqual(state.detections, {})
    assert.equal(state.latest.scenario, 'b')
    assert.equal(state.reopenPlan.est_hours_saved, 9)

    const osm = JSON.parse(readFileSync(path.join(__dirname, '../public/data/harbor-osm.geojson'), 'utf8'))
    assert.ok(parseLocalBase(osm).features.length > 0)
    assert.ok(osm.features.some(feature => feature.properties.kind === 'coastline'))
    assert.match(osm.license, /ODbL/)
    assert.throws(() => parseLocalBase({ type: 'FeatureCollection', features: [] }))
    const detection = a.find(row => row.msg.event === 'detection').msg.data.detection
    assert.equal(localSonarPath(detection), '/data/sonar-stub.svg')
    for (const image_url of ['https://example.com/sonar.png', '//localhost:8000/a.png', '/api/sonar/a.png', '/x/../a.png', '']) assert.equal(localSonarPath({ ...detection, image_url }), '/sonar/det-1.png')
    assert.deepEqual(metricEntries(null), [])
    assert.deepEqual(metricEntries({ map50: .82, recall: { uuv: .9 } }), [['map50', '0.82'], ['recall', '{"uuv":0.9}']])

    const calls = []
    global.fetch = async (url) => { calls.push(url); return url === '/data/harbor-osm.geojson' ? new Response(JSON.stringify(osm)) : new Response('', { status: 404 }) }
    await Promise.all([loadLocalBase(), loadLocalBase()])
    assert.equal(calls.filter(url => url === '/data/harbor-osm.geojson').length, 1)
    cleanup = startMock(); await loadLocalData()
    const engine = getMock()
    assert.ok(engine)
    await api.startScenario('b', 10); engine.advance(4.5)
    assert.equal(useHarbor.getState().reopenPlan.est_hours_saved, 9)
    const before = calls.length
    assert.deepEqual(await api.metrics(), { yolo: null, lora: null })
    assert.equal(calls.length, before)
    cleanup(); cleanup = null

    useHarbor.setState(rebuildReplay(a, a.length, useHarbor.getState()))
    for (const command of [() => api.startScenario('b'), () => api.control({ action: 'reset' }), () => api.mode('disaster'), () => api.inject({ type: 'network_down' }), () => api.ask('Test'), () => api.postLog({ level: 'info', source: 'operator', text: 'Test' }), () => api.postRecommendation(useHarbor.getState().latestRec)]) await assert.rejects(command, /disabled during replay/)
    assert.equal(calls.length, before)
    // Lifecycle: loading/seek/speed/cleanup work from a local file without a running backend.
    global.fetch = async url => { calls.push(url); return new Response(a.map(JSON.stringify).join('\n')) }
    cleanup = startReplay('demo_a.jsonl')
    await new Promise(resolve => setImmediate(resolve))
    assert.equal(useReplay.getState().loading, false)
    assert.equal(useReplay.getState().duration, 90000)
    useReplay.getState().driver.seek(70000)
    assert.equal(useHarbor.getState().decisionsByAlert.A1.action, 'approve')
    useReplay.getState().driver.setSpeed(2)
    assert.equal(useReplay.getState().speed, 2)
    useReplay.getState().driver.seek(35000)
    useHarbor.getState().selectTrack('T3')
    useReplay.getState().driver.play(true)
    await new Promise(resolve => setTimeout(resolve, 260))
    useReplay.getState().driver.play(false)
    assert.equal(useHarbor.getState().selectedTrackId, 'T3', 'pause/resume must retain the selected vessel')
    const pausedT3 = useHarbor.getState().tracks.T3
    await new Promise(resolve => setTimeout(resolve, 100))
    assert.equal(useHarbor.getState().tracks.T3, pausedT3)
    cleanup(); cleanup = null
    assert.equal(useReplay.getState().driver, null)
    assert.deepEqual(calls.slice(before), ['/demo_a.jsonl'])
    global.fetch = async () => new Response('', { status: 404 })
    cleanup = startReplay('missing.jsonl')
    await new Promise(resolve => setImmediate(resolve))
    assert.match(useReplay.getState().error, /404/)
    cleanup(); cleanup = null
    assert.equal(useHarbor.getState().conn, 'replay')
    console.log('PASS A5: disaster fixtures / direct reopening numbers; offline OSM vector provenance/cache; synthetic sonar and local-only paths; metrics null/raw values; JSONL validation; seeks restore all caches and scenario resets; wall-time pause/1x/2x/end/restart; replay POST lock; local loading/error/cleanup. No browser/GPU/backend claims.')
  } finally { cleanup?.(); global.fetch = originalFetch }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
