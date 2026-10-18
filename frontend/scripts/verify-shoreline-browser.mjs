// Optional browser acceptance harness; Playwright is supplied externally, not a
// runtime dependency. Both URLs must serve production builds on this machine.
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createRequire } from 'node:module'
import path from 'node:path'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.HARBORGUARD_PLAYWRIGHT || 'playwright')
const [before = 'http://127.0.0.1:4177', after = 'http://127.0.0.1:4176', output = 'artifacts/underwater-fix'] = process.argv.slice(2)
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.HARBORGUARD_CHROMIUM, args: process.platform === 'darwin' ? ['--use-angle=metal'] : [] })
const evidence = process.env.HARBORGUARD_ONLY === 'after' ? JSON.parse(await readFile(path.join(output,'browser-evidence.json'),'utf8')) : { viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, samplesPerView: 12, results: {} }
async function pageFor(url, query, errors) {
  const p = await browser.newPage({ viewport: evidence.viewport, deviceScaleFactor: 1 })
  // Isolate an unrelated metrics endpoint equally in both rendering builds.
  await p.route('http://localhost:8000/api/metrics', route => route.fulfill({json:{yolo:null,lora:null}}))
  p.on('pageerror', e => errors.push(String(e)))
  p.on('console', m => { if (m.type() === 'error') errors.push(m.text()) })
  await p.goto(`${url}/?${query}`, { waitUntil: 'domcontentloaded' })
  await p.getByRole('button', { name: '3D View', exact: true }).click()
  await p.getByRole('button', { name: 'Underwater', exact: true }).waitFor({ timeout: 120000 })
  await p.waitForFunction(() => /487/.test(document.querySelector('.three-environment-note')?.textContent ?? ''), null, { timeout: 120000 })
  await p.waitForTimeout(2500)
  return p
}
try {
  for (const [name, url] of [['before', before], ['after', after]].filter(([name]) => !process.env.HARBORGUARD_ONLY || name === process.env.HARBORGUARD_ONLY)) {
    const errors = [], result = { errors, frames: {}, interactions: [], screenshots: [] }
    // Paused t=0 replay, unchanged presets, canvas and 3× scale: matched images.
    const still = await pageFor(url, 'replay=demo_full.jsonl&stats=1', errors)
    for (const mode of ['Underwater', 'Surface', 'Overview']) {
      await still.getByRole('button', { name: mode, exact: true }).click()
      await still.waitForTimeout(2200)
      const file = `${name}-${mode.toLowerCase()}.png`
      await still.screenshot({ path: path.join(output, file) })
      result.screenshots.push(file)
    }
    result.canvas = await still.locator('canvas').evaluate(c => {
      const gl = c.getContext('webgl2'), debug = gl.getExtension('WEBGL_debug_renderer_info')
      return { css: { width: c.clientWidth, height: c.clientHeight }, buffer: { width: c.width, height: c.height }, renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER), antialias: gl.getContextAttributes().antialias }
    })
    await still.close()
    // Separate running Scenario A benchmark. Reset at each preset so the same
    // simulation window is sampled; this is not a paused-scene FPS claim.
    const p = await pageFor(url, 'mock=1&stats=1', errors)
    for (const mode of ['Underwater', 'Surface', 'Overview', 'Follow Selected']) {
      await p.getByRole('button', { name: 'Scenario A', exact: true }).click()
      await p.waitForTimeout(3000)
      if (mode === 'Follow Selected') {
        const select = p.getByLabel('Select 3D target')
        const ids = await select.locator('option').evaluateAll(options => options.map(o => o.value).filter(Boolean))
        if (!ids.length) throw new Error('No simulated target available for Follow Selected')
        result.followTarget = ids.includes('T3') ? 'T3' : ids[0]
        await select.selectOption(result.followTarget)
      }
      await p.getByRole('button', { name: mode, exact: true }).click()
      await p.waitForTimeout(2200)
      const samples = []
      for (let i = 0; i < evidence.samplesPerView; i++) {
        await p.waitForTimeout(1000)
        samples.push(Number(await p.locator('.three-fps strong').textContent()))
      }
      result.frames[mode] = { samples, mean: samples.reduce((a,b) => a+b,0)/samples.length, minimum: Math.min(...samples) }
    }
    if (name === 'after') {
      await p.locator('.three-display-controls > summary').click()
      for (const label of ['MSAA + FXAA','Distance & depth scattering','Water Fresnel & ripples (illustrative)','Seabed detail normals (illustrative)','Wet-sand transition (illustrative)','Caustics (illustrative, extra cost)','Smooth land heightfield (display only)','Quay closure to model floor (illustrative)']) {
        const input = p.getByLabel(label, { exact: true }), original = await input.isChecked()
        await input.setChecked(!original); await p.waitForTimeout(250)
        await input.setChecked(original)
        result.interactions.push(label)
      }
      await p.getByLabel('Vertical exaggeration').selectOption('1')
      await p.getByLabel('Vertical exaggeration').selectOption('3')
      await p.locator('.three-display-controls > summary').click()
      await p.locator('.three-layer-controls > summary').click()
      const fill = p.getByLabel('Regional model fill (not surveyed)', { exact: true })
      await fill.uncheck(); await p.waitForTimeout(500); await fill.check()
      await p.locator('.three-layer-controls > summary').click()
      await p.getByRole('button', { name: 'Underwater', exact: true }).click()
      await p.waitForTimeout(2000)
      const box = await p.locator('canvas').boundingBox(), x = box.x+box.width*.6, y = box.y+box.height*.58
      await p.mouse.move(x,y);await p.mouse.down();await p.mouse.move(x+90,y+25,{steps:20});await p.mouse.up()
      await p.mouse.wheel(0,-250);await p.waitForTimeout(1200)
      await p.screenshot({ path: path.join(output, 'after-orbit-zoom.png') })
      result.interactions.push('1× / 3× restore', 'Regional fill off/on', 'Orbit and zoom', 'Follow Selected')
      const text = await p.locator('.three-stage').textContent()
      for (const required of ['Not for navigation','enhanced, not true scale','Water 0 m (reference, not live tide)','simulated data','Regional model fill (not surveyed)']) {
        if (!text.includes(required)) throw new Error(`Missing disclosure: ${required}`)
      }
      result.disclosures = 'PASS'
    }
    await p.close()
    evidence.results[name] = result
    await writeFile(path.join(output, 'browser-evidence.json'), JSON.stringify(evidence, null, 2)+'\n')
    console.log(name, JSON.stringify(result.frames), 'errors', errors.length)
    if (errors.length) throw new Error(`${name}: browser errors: ${errors.join('\n')}`)
  }
} finally { await browser.close() }
