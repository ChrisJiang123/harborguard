const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
writeFileSync(path.join(__dirname, '../work/verify-a2/package.json'), '{"type":"commonjs"}\n')
const { ORIGIN, PORT_CENTER, toLocal, toLatLon, errorEllipse, trailPositions } = require('../work/verify-a2/map2d/geo.js')
const { zoneStyle, targetIconHTML, buoyIconHTML } = require('../work/verify-a2/map2d/styles.js')
const { parseZones, parseAssets, parseBuoys, polygonPositions } = require('../work/verify-a2/data/mapGeometry.js')
const { DEMO_ASSETS, DEMO_BUOYS, DEMO_ZONES } = require('../work/verify-a2/data/demoGeometry.js')
const { loadLocalData } = require('../work/verify-a2/data/staticData.js')
const { createMockEngine } = require('../work/verify-a2/data/mock.js')
const { receiveMessage, useHarbor } = require('../work/verify-a2/store/useHarbor.js')

const near = (actual, expected, epsilon = 1e-7) => assert.ok(Math.abs(actual - expected) < epsilon, `${actual} != ${expected}`)

async function main() {
  assert.deepEqual(PORT_CENTER, [33.735, -118.255])
  assert.deepEqual(toLocal(ORIGIN.lat, ORIGIN.lon), [0, 0])
  const point = toLatLon(1000, -500)
  const restored = toLocal(...point)
  near(restored[0], 1000)
  near(restored[1], -500)
  assert.ok(toLatLon(100, 0)[1] > ORIGIN.lon)
  assert.ok(toLatLon(0, 100)[0] > ORIGIN.lat)

  const ellipse = errorEllipse({ ...ORIGIN, err: { a_m: 100, b_m: 50, angle_deg: 90 } })
  assert.equal(ellipse.length, 36)
  const ellipsePoint = toLocal(...ellipse[0])
  near(ellipsePoint[0], 0)
  near(ellipsePoint[1], 100)
  const quarter = toLocal(...ellipse[9])
  near(quarter[0], -50)
  near(quarter[1], 0)
  assert.deepEqual(trailPositions([[33, -118, 12, 0], [NaN, -118, 12, 1]]), [[33, -118]])

  assert.equal(DEMO_ZONES.features.length, 10)
  assert.equal(DEMO_BUOYS.length, 10)
  assert.ok(parseZones(DEMO_ZONES))
  assert.ok(parseAssets(DEMO_ASSETS))
  assert.ok(parseBuoys(DEMO_BUOYS))
  assert.equal(parseZones({ type: 'FeatureCollection', features: [] }), null)
  assert.equal(parseZones({ ...DEMO_ZONES, features: [DEMO_ZONES.features[0], DEMO_ZONES.features[0]] }), null)
  assert.equal(parseZones({ ...DEMO_ZONES, features: [{ ...DEMO_ZONES.features[0], geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1]]] } }] }), null)
  assert.equal(parseAssets([{ ...DEMO_ASSETS[0], lat: 200 }]), null)
  assert.equal(parseBuoys([{ ...DEMO_BUOYS[0], range_m: -1 }]), null)
  const multi = { type: 'MultiPolygon', coordinates: [[[[0, 0], [1, 0], [1, 1], [0, 0]], [[.1, .1], [.2, .1], [.2, .2], [.1, .1]]], [[[2, 2], [3, 2], [3, 3], [2, 2]]]] }
  const positions = polygonPositions(multi)
  assert.equal(positions.length, 2)
  assert.equal(positions[0].length, 2)
  assert.deepEqual(positions[0][0][1], [0, 1])

  assert.equal(zoneStyle('open').fillOpacity, 0)
  assert.equal(zoneStyle('restricted').fillOpacity, .25)
  assert.equal(zoneStyle('open', true).color, '#EF4444')
  assert.equal(zoneStyle('open', true).dashArray, '8 5')
  assert.match(targetIconHTML('uuv', 3, true), /is-selected/)
  assert.match(targetIconHTML('uuv', 3, true), /#EF4444/)
  assert.match(buoyIconHTML('down'), /×/)

  const originalFetch = global.fetch
  const requests = []
  try {
    global.fetch = async url => { requests.push(String(url)); return new Response('<html>missing file</html>', { status: 200, headers: { 'content-type': 'text/html' } }) }
    const [first, second] = await Promise.all([loadLocalData(true), loadLocalData()])
    assert.equal(first, second)
    assert.equal(requests.length, 3)
    assert.equal(first.sources.zones, 'demo')
    assert.equal(first.zones.features.length, 10)

    const teamZones = { ...DEMO_ZONES, features: DEMO_ZONES.features.map((zone, i) => ({ ...zone, properties: { ...zone.properties, id: `team-${i + 1}` } })) }
    const teamAsset = { ...DEMO_ASSETS[0], id: 'asset-team', lat: 33.74, lon: -118.25 }
    global.fetch = async url => {
      requests.push(String(url))
      const body = String(url).includes('zones') ? teamZones : String(url).includes('assets') ? [teamAsset] : DEMO_BUOYS
      return new Response(JSON.stringify(body), { headers: { 'content-type': 'application/json' } })
    }
    const resources = await loadLocalData(true)
    assert.deepEqual(resources.sources, { zones: 'file', assets: 'file', buoys: 'file' })
    const messages = []
    useHarbor.getState().reset()
    const engine = createMockEngine(msg => { messages.push(msg); receiveMessage(msg) }, resources.buoys, resources.assets[0], resources.zones.features.map(zone => zone.properties.id))
    engine.start()
    // Five minutes of simulation verifies bounded history and correctly aligned team IDs.
    for (let i = 0; i < 1500; i++) engine.advance(.2)
    const state = useHarbor.getState()
    assert.equal(state.latest.t, 300)
    assert.equal(state.tracks.T1.history.length, 60)
    assert.equal(state.tracks.T1.lat, teamAsset.lat)
    assert.equal(state.tracks.T1.lon, teamAsset.lon)
    assert.equal(state.alerts.A1.asset_id, teamAsset.id)
    assert.ok(state.optionsByAlert.A1.every(option => option.zones_closed.every(id => id.startsWith('team-'))))
    engine.decision({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: 'test' })
    assert.deepEqual(useHarbor.getState().latest.zones.filter(zone => zone.state === 'restricted').map(zone => zone.id), ['team-4', 'team-5'])
    useHarbor.getState().selectTrack('T1')
    engine.advance(.2)
    assert.equal(useHarbor.getState().selectedTrackId, 'T1')
    receiveMessage({ type: 'event', seq: 99999, t: 301, event: 'buoy_changed', data: { buoy_id: 'B1', status: 'down' } })
    assert.equal(useHarbor.getState().latest.buoys.find(buoy => buoy.id === 'B1').status, 'down')
    assert.ok(messages.length < 1550)
    engine.stop()

    // Verify startup API loading with mocked responses only; this test makes no network requests.
    const ts = require('typescript')
    const Module = require('node:module')
    const loaderPath = path.join(__dirname, '../src/store/useMapData.ts')
    const loaderCode = ts.transpileModule(readFileSync(loaderPath, 'utf8').replace('import.meta.env.VITE_API_BASE', 'undefined'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 } }).outputText
    const loader = new Module(loaderPath, module)
    loader.require = name => name.startsWith('../data/') ? require(path.join(__dirname, '../work/verify-a2/data/', name.slice('../data/'.length) + '.js')) : require(name)
    loader._compile(loaderCode, loaderPath)
    const originalLocation = global.location
    try {
      global.location = { search: '' }
      const beforeAPI = requests.length
      const loadOne = loader.exports.ensureMapData()
      const loadTwo = loader.exports.ensureMapData()
      assert.equal(loadOne, loadTwo)
      await loadOne
      assert.deepEqual(loader.exports.useMapData.getState().resources.sources, { zones: 'api', assets: 'api', buoys: 'api' })
      await loader.exports.ensureMapData()
      assert.equal(requests.length - beforeAPI, 3)
      assert.deepEqual(requests.slice(-3), ['http://localhost:8000/api/zones', 'http://localhost:8000/api/assets', 'http://localhost:8000/api/buoys'])
    } finally {
      if (originalLocation === undefined) delete global.location
      else global.location = originalLocation
    }
  } finally { global.fetch = originalFetch }
  console.log('PASS A2: metre/latlon roundtrip; 36-point ellipse; polygon holes/islands; GeoJSON validation; 10 zones/buoys; level/selection/offline styles; cached static/API loading; 5-minute simulation; team ID alignment; buoy-down event.')
}
main().catch(error => { console.error(error); process.exitCode = 1 })
