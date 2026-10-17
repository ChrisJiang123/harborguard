const { writeFileSync } = require('node:fs')
const path = require('node:path')
const { createMockEngine } = require('../work/verify-a5/data/mock.js')

function save(filename, rows) {
  writeFileSync(path.join(__dirname, '../public', filename), rows.map(row => JSON.stringify(row)).join('\n') + '\n')
  console.log(`Saved ${filename}: ${rows.length} synthetic messages; not a B backend recording.`)
}

function recordScenario(scenario) {
  const rows = []
  const engine = createMockEngine(msg => rows.push({ wall_ms: Math.round(msg.t * 1000), msg }))
  engine.startScenario(scenario)
  for (let step = 1; step <= (scenario === 'a' ? 450 : 300); step++) {
    engine.advance(.2)
    if (step === 150) engine.inject({ type: 'buoy_down', target: 'B1' })
    if (step === 250) engine.inject({ type: 'network_down' })
    if (scenario === 'a' && step === 350) engine.decision({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: '模拟操作员（录制事件）' })
  }
  engine.stop()
  return rows
}

for (const scenario of ['a', 'b']) save(`demo_${scenario}.jsonl`, recordScenario(scenario))

function recordFullDemo() {
  const rows = []
  let wallOffset = 0
  const engine = createMockEngine(msg => rows.push({ wall_ms: wallOffset + Math.round(msg.t * 1000), msg }))

  engine.startScenario('a')
  for (let step = 1; step <= 400; step++) {
    engine.advance(.2)
    if (step === 350) engine.decision({ alert_id: 'A1', option_id: 'opt-1', action: 'approve', operator: '模拟操作员（录制事件）' })
  }

  wallOffset = 80_000
  engine.startScenario('b')
  for (let step = 1; step <= 500; step++) {
    engine.advance(.2)
    if (step === 230) engine.inject({ type: 'buoy_down', target: 'B1' })
    if (step === 240) engine.inject({ type: 'network_down' })
  }
  engine.stop()
  return rows
}

save('demo_full.jsonl', recordFullDemo())
