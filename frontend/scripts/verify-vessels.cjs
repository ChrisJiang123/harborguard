const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const root = path.join(__dirname, '../work/verify-vessels')
writeFileSync(path.join(root, 'package.json'), '{"type":"commonjs"}\n')
const { demoVesselTrack, sampleDemoVessel, demoVesselDuration } = require(path.join(root, 'data/vesselMotion.js'))
const { createMockEngine } = require(path.join(root, 'data/mock.js'))
const { toLocal } = require(path.join(root, 'map2d/geo.js'))
const { blendHeading } = require(path.join(root, 'view3d/coordinates.js'))
const { parseReplay, rebuildReplay } = require(path.join(root, 'data/replayCore.js'))
const { useHarbor } = require(path.join(root, 'store/useHarbor.js'))
const dem = JSON.parse(readFileSync(path.join(__dirname, '../public/data/seabed-dem.json'), 'utf8'))
const near = (a, b, tolerance = 1e-7) => assert.ok(Math.abs(a - b) <= tolerance, `${a} != ${b}`)
const angle = (a, b) => Math.abs(((a - b + 540) % 360 + 360) % 360 - 180)
let maximumAcceleration = 0, maximumTurnRate = 0, minimumDepth = Infinity, minimumSeparation = Infinity
function checkWater(lat, lon) {
  const { bounds, width, height, nodata_value } = dem.metadata
  const column = Math.floor((lon - bounds.west) / (bounds.east - bounds.west) * (width - 1))
  const row = Math.floor((bounds.north - lat) / (bounds.north - bounds.south) * (height - 1))
  assert.ok(column >= 0 && column < width - 1 && row >= 0 && row < height - 1)
  for (const index of [row * width + column, row * width + column + 1, (row + 1) * width + column, (row + 1) * width + column + 1]) {
    const depth = dem.values[index]
    assert.notEqual(depth, nodata_value, `demo vessel intersects land/NoData at ${lat}, ${lon}`)
    assert.ok(depth >= 7, `demo corridor enters a shallow regional grid cell: ${depth} m`)
    minimumDepth = Math.min(minimumDepth, depth)
  }
}
for (const id of ['T3', 'T4']) {
  for (let t = -500; t < 0; t++) { const point = sampleDemoVessel(id, t); checkWater(point.lat, point.lon) }
  let previous = sampleDemoVessel(id, 0)
  for (let t = .2; t <= demoVesselDuration(id) + 5; t = Math.round((t + .2) * 10) / 10) {
    const current = sampleDemoVessel(id, t)
    checkWater(current.lat, current.lon)
    near(Math.hypot(current.vel_e, current.vel_n), current.speed)
    assert.ok(current.speed >= 0 && current.speed <= 3.8 + 1e-6)
    maximumAcceleration = Math.max(maximumAcceleration, Math.abs(current.speed - previous.speed) / .2)
    maximumTurnRate = Math.max(maximumTurnRate, angle(current.heading, previous.heading) / .2)
    const a = toLocal(previous.lat, previous.lon), b = toLocal(current.lat, current.lon)
    near(Math.hypot(b[0] - a[0], b[1] - a[1]) / .2, (previous.speed + current.speed) / 2, .015)
    if (current.speed > .01) assert.ok(angle(current.heading, Math.atan2(current.vel_e, current.vel_n) * 180 / Math.PI) < 1e-6)
    previous = current
  }
  const stop = sampleDemoVessel(id, demoVesselDuration(id)), later = sampleDemoVessel(id, demoVesselDuration(id) + 500)
  assert.deepEqual(stop, later, 'end position and heading must hold with zero speed, not jump north')
  assert.equal(stop.speed, 0)
  for (const t of [0, 35, 80, 130, demoVesselDuration(id) + 10]) {
    const track = demoVesselTrack(id, t)
    assert.ok(track.history.length <= 60 && track.history.every(point => point[3] >= 0))
    near(track.history.at(-1)[0], track.lat)
    near(track.history.at(-1)[1], track.lon)
    for (const [lat, lon, depth, time] of track.predicted) {
      const future = sampleDemoVessel(id, time)
      near(lat, future.lat); near(lon, future.lon); assert.equal(depth, 0)
      checkWater(lat, lon)
    }
  }
}
assert.ok(maximumAcceleration <= .04501, `acceleration ${maximumAcceleration}`)
assert.ok(maximumTurnRate < 3, `turn rate ${maximumTurnRate}`)
for (let t = 0; t <= Math.max(demoVesselDuration('T3'), demoVesselDuration('T4')); t++) {
  const a = sampleDemoVessel('T3', t), b = sampleDemoVessel('T4', t)
  const pa = toLocal(a.lat, a.lon), pb = toLocal(b.lat, b.lon)
  minimumSeparation = Math.min(minimumSeparation, Math.hypot(pa[0] - pb[0], pa[1] - pb[1]))
}
assert.ok(minimumSeparation > 55, `opposing demo vessels are too close: ${minimumSeparation}`)
assert.ok(blendHeading(359, 1, .05) > 359, 'heading must turn through north, not spin 358 degrees')
assert.ok(blendHeading(1, 359, .05) < 1)

const rows = [], engine = createMockEngine(msg => rows.push(msg))
const lastState = messages => messages.findLast(msg => msg.type === 'state')
engine.startScenario('a'); engine.advance(40)
const beforePause = lastState(rows).tracks.filter(track => track.cls === 'vessel')
engine.control('pause'); engine.advance(10)
assert.deepEqual(lastState(rows).tracks.filter(track => track.cls === 'vessel'), beforePause)
engine.control('resume'); engine.advance(1)
assert.notEqual(lastState(rows).tracks.find(track => track.id === 'T3').lat, beforePause[0].lat)
const at41 = lastState(rows).tracks.find(track => track.id === 'T3')
const independent = [], other = createMockEngine(msg => independent.push(msg))
other.startScenario('a'); for (let i = 0; i < 205; i++) other.advance(.2)
assert.deepEqual(at41, lastState(independent).tracks.find(track => track.id === 'T3'), 'trajectory must not depend on tick chunk size')
engine.startScenario('b')
assert.deepEqual(lastState(rows).tracks.filter(track => track.cls === 'vessel'), ['T3', 'T4'].map(id => demoVesselTrack(id, 0)))
for (const file of ['demo_a.jsonl', 'demo_b.jsonl', 'demo_full.jsonl']) {
  const replay = parseReplay(readFileSync(path.join(__dirname, '../public', file), 'utf8'))
  for (const wall of [0, 35000, 70000, 90000, 125000, 180000]) {
    const end = replay.filter(row => row.wall_ms <= wall).length
    const state = rebuildReplay(replay, end, useHarbor.getState())
    for (const id of ['T3', 'T4']) assert.deepEqual(state.tracks[id], demoVesselTrack(id, state.latest.t), `${file}: seek ${wall}, ${id}`)
  }
}
console.log(`PASS vessel motion: full-route water-mask checks (minimum source-cell depth ${minimumDepth} m); max acceleration ${maximumAcceleration.toFixed(4)} m/s²; max sampled turn ${maximumTurnRate.toFixed(3)} deg/s; minimum simultaneous separation ${minimumSeparation.toFixed(1)} m; velocity/course consistency; braking/zero-speed endpoint; bounded history and coherent prediction; pause/resume/reset; chunk-independent time; replay seeks. Synthetic routes, not AIS or navigational clearance.`)
