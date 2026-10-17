const assert = require('node:assert/strict')
const { readFileSync, writeFileSync } = require('node:fs')
const path = require('node:path')
const root = path.join(__dirname,'../work/verify-sonar')
writeFileSync(path.join(root,'package.json'),'{"type":"commonjs"}\n')
const { PROPOSED_SONARS, proposedSonar } = require(path.join(root,'data/sonarDeployment.js'))
const { DEMO_BUOYS } = require(path.join(root,'data/demoGeometry.js'))
const { sampleDemoVessel, demoVesselDuration } = require(path.join(root,'data/vesselMotion.js'))
const { toLocal } = require(path.join(root,'map2d/geo.js'))
const { createMockEngine } = require(path.join(root,'data/mock.js'))
const { parseReplay, rebuildReplay } = require(path.join(root,'data/replayCore.js'))
const { useHarbor } = require(path.join(root,'store/useHarbor.js'))
const json = file => JSON.parse(readFileSync(path.join(__dirname,'../public',file),'utf8'))
const grid = json('data/seabed-dem.json'), m = grid.metadata
assert.deepEqual(json('data/buoys.json'),DEMO_BUOYS)
assert.equal(new Set(PROPOSED_SONARS.map(p=>p.id)).size,10)
let minimumDepth=Infinity, minimumRouteOffset=Infinity
for (const buoy of PROPOSED_SONARS) {
  const col=Math.floor((buoy.lon-m.bounds.west)/(m.bounds.east-m.bounds.west)*(m.width-1))
  const row=Math.floor((m.bounds.north-buoy.lat)/(m.bounds.north-m.bounds.south)*(m.height-1))
  const index=row*m.width+col
  for (const i of [index,index+1,index+m.width,index+m.width+1]) {
    const depth=grid.values[i]
    assert.notEqual(depth,m.nodata_value,`${buoy.id}: no supported water depth`)
    assert.ok(depth>buoy.head_depth_m+2,`${buoy.id}: head must remain above supported floor`)
    minimumDepth=Math.min(minimumDepth,depth)
  }
  const point=toLocal(buoy.lat,buoy.lon)
  for (const id of ['T3','T4']) for(let t=-500;t<=demoVesselDuration(id);t+=1) {
    const vessel=sampleDemoVessel(id,t), position=toLocal(vessel.lat,vessel.lon)
    const distance=Math.hypot(point[0]-position[0],point[1]-position[1])
    minimumRouteOffset=Math.min(minimumRouteOffset,distance)
    assert.ok(distance>50,`${buoy.id} is too close to demo ${id} path: ${distance} m`)
  }
  assert.equal(proposedSonar(buoy),buoy)
  assert.equal(proposedSonar({...buoy,lat:buoy.lat+.0001}),undefined,'do not attach proposed depth to unrelated live/recorded positions')
}
const messages=[]
const engine=createMockEngine(msg=>messages.push(msg))
engine.start();engine.advance(40)
assert.deepEqual(messages.filter(msg=>msg.type==='state').at(-1).buoys.map(({id,lat,lon,range_m})=>({id,lat,lon,range_m})),DEMO_BUOYS)
engine.stop()
for (const file of ['demo_a.jsonl','demo_b.jsonl','demo_full.jsonl']) {
  const replay=parseReplay(readFileSync(path.join(__dirname,'../public',file),'utf8'))
  for(const at of [0,20000,45000]) {
    const end=replay.filter(row=>row.wall_ms<=at).length
    const state=rebuildReplay(replay,end,useHarbor.getState())
    assert.deepEqual(state.latest.buoys.map(({id,lat,lon,range_m})=>({id,lat,lon,range_m})),DEMO_BUOYS,`${file}: seek must restore same proposed positions`)
  }
}
console.log(`PASS proposed sonar layout: 10 stations in supported H12617 water; minimum floor depth ${minimumDepth.toFixed(2)} m; minimum sampled vessel-path offset ${minimumRouteOffset.toFixed(1)} m; file/mock/replay equality; no relocation of unrelated positions. Not a site deployment or acoustic-coverage certification.`)
