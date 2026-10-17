const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const root = path.join(__dirname, '../work/verify-a6')
writeFileSync(path.join(root, 'package.json'), '{"type":"commonjs"}\n')
const { RECORDING_LIMIT_MS, RECORDING_MAX_BYTES, RECORDING_MIMES, recordStream, videoExtension } = require(path.join(root, 'recording.js'))

class FakeTrack {
  stopped = 0
  listeners = new Map()
  stop() { this.stopped++ }
  addEventListener(name, callback) { this.listeners.set(name, callback) }
  removeEventListener(name, callback) { if (this.listeners.get(name) === callback) this.listeners.delete(name) }
}

class FakeRecorder {
  static supported = true
  static instances = []
  static isTypeSupported(mime) { return this.supported && mime.includes('vp8') }
  state = 'inactive'
  mimeType
  ondataavailable = null
  onerror = null
  onstop = null
  constructor(_stream, options) { this.mimeType = options.mimeType; FakeRecorder.instances.push(this) }
  start(slice) { this.slice = slice; this.state = 'recording' }
  stop() {
    if (this.state === 'inactive') return
    this.state = 'inactive'
    this.ondataavailable?.({ data: new Blob(['harborguard-video']) })
    this.onstop?.()
  }
}

function harness() {
  let now = 0, ticker, deadline
  const track = new FakeTrack()
  const stream = { getTracks: () => [track], getVideoTracks: () => [track] }
  const runtime = {
    Recorder: FakeRecorder,
    now: () => now,
    every: callback => { ticker = callback; return 1 },
    cancelEvery: () => { ticker = undefined },
    later: callback => { deadline = callback; return 2 },
    cancelLater: () => { deadline = undefined },
  }
  return { stream, track, runtime, setNow: value => { now = value }, tick: () => ticker?.(), deadline: () => deadline?.() }
}

assert.equal(RECORDING_LIMIT_MS, 180_000)
assert.equal(RECORDING_MAX_BYTES, 120_000_000)
assert.deepEqual(RECORDING_MIMES, ['video/webm;codecs=vp8', 'video/webm', 'video/mp4'])
assert.equal(videoExtension('video/mp4'), 'mp4')
assert.equal(videoExtension('video/webm;codecs=vp8'), 'webm')

{
  const h = harness()
  const progress = [], completed = [], errors = []
  const active = recordStream(h.stream, { progress: ms => progress.push(ms), complete: (blob, ms) => completed.push([blob, ms]), error: message => errors.push(message) }, h.runtime)
  assert.equal(FakeRecorder.instances.at(-1).slice, 1000)
  assert.equal(FakeRecorder.instances.at(-1).mimeType, 'video/webm;codecs=vp8')
  h.setNow(1234); h.tick()
  assert.deepEqual(progress, [1234])
  active.stop()
  assert.equal(completed.length, 1)
  assert.equal(completed[0][0].size, 17)
  assert.equal(completed[0][1], 1234)
  assert.deepEqual(errors, [])
  assert.equal(h.track.stopped, 1)
  assert.equal(h.track.listeners.size, 0)
}

{
  const h = harness()
  let completed = false
  const active = recordStream(h.stream, { progress() {}, complete() { completed = true }, error: assert.fail }, h.runtime)
  active.cancel()
  assert.equal(completed, false)
  assert.equal(h.track.stopped, 1)
}

{
  const h = harness()
  let elapsed = 0
  recordStream(h.stream, { progress() {}, complete(_blob, ms) { elapsed = ms }, error: assert.fail }, h.runtime)
  h.setNow(RECORDING_LIMIT_MS); h.deadline()
  assert.equal(elapsed, RECORDING_LIMIT_MS)
  assert.equal(h.track.stopped, 1)
}

{
  FakeRecorder.supported = false
  const h = harness()
  assert.throws(() => recordStream(h.stream, { progress() {}, complete() {}, error() {} }, h.runtime), /不支持/)
  assert.equal(h.track.stopped, 1)
  FakeRecorder.supported = true
}

const rows = readFileSync(path.join(__dirname, '../public/demo_full.jsonl'), 'utf8').trim().split(/\r?\n/).map(JSON.parse)
assert.ok(rows.length > 900)
assert.equal(rows[0].wall_ms, 0)
assert.equal(rows.at(-1).wall_ms, 180_000)
for (let i = 1; i < rows.length; i++) assert.ok(rows[i].wall_ms >= rows[i - 1].wall_ms, `wall_ms reversed at row ${i + 1}`)
assert.ok(rows.some(row => row.msg.type === 'state' && row.msg.scenario === 'a'))
assert.ok(rows.some(row => row.msg.type === 'event' && row.msg.event === 'decision' && row.msg.data.action === 'approve'))
assert.ok(rows.some(row => row.wall_ms === 80_000 && row.msg.type === 'event' && row.msg.event === 'scenario_changed' && row.msg.data.scenario === 'b'))
assert.ok(rows.some(row => row.msg.type === 'event' && row.msg.event === 'reopen_plan'))
assert.ok(rows.some(row => row.msg.type === 'state' && row.msg.scenario === 'b' && row.msg.network === 'offline' && row.msg.buoys.some(buoy => buoy.status === 'down')))
const vesselStates = rows.filter(row => row.msg.type === 'state' && row.msg.tracks.some(track => track.id === 'T3'))
assert.ok(vesselStates.length > 2)
const firstVessel = vesselStates[0].msg.tracks.find(track => track.id === 'T3')
const lastVessel = vesselStates.at(-1).msg.tracks.find(track => track.id === 'T3')
assert.equal(firstVessel.cls, 'vessel')
assert.ok(Number.isFinite(firstVessel.heading_deg))
assert.notEqual(lastVessel.lon, firstVessel.lon)

const demoTools = readFileSync(path.join(__dirname, '../src/panels/DemoTools.tsx'), 'utf8')
const recordingHook = readFileSync(path.join(__dirname, '../src/demo/useRecording.ts'), 'utf8')
assert.match(demoTools, /replay=demo_full\.jsonl/)
assert.match(demoTools, /1920 × 1080/)
assert.match(recordingHook, /audio: false/)
assert.doesNotMatch(recordingHook, /getUserMedia/)

console.log('PASS A6: three-minute combined synthetic replay with moving vessels; scenario transition and reset; approval, reopening, buoy/offline events; 180-second recording cap; local-only screen capture without audio; cleanup, cancellation and format fallback.')
