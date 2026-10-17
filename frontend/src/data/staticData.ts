import { DEMO_ASSETS, DEMO_BUOYS, DEMO_ZONES } from './demoGeometry'
import { parseAssets, parseBuoys, parseZones } from './mapGeometry'
import type { MapResources } from './mapGeometry'

export async function fetchJSON(url: string, timeoutMs = 3000): Promise<unknown> {
  const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) })
  if (!response.ok || !response.headers.get('content-type')?.includes('json')) throw new Error('图层文件未就绪')
  return response.json()
}

let localPromise: Promise<MapResources> | undefined
export function loadLocalData(force = false): Promise<MapResources> {
  if (force) localPromise = undefined
  localPromise ??= (async () => {
    const result = await Promise.allSettled([
      fetchJSON('/data/zones.geojson'), fetchJSON('/data/assets.json'), fetchJSON('/data/buoys.json'),
    ])
    const zones = result[0].status === 'fulfilled' ? parseZones(result[0].value) : null
    const assets = result[1].status === 'fulfilled' ? parseAssets(result[1].value) : null
    const buoys = result[2].status === 'fulfilled' ? parseBuoys(result[2].value) : null
    return { zones: zones ?? DEMO_ZONES, assets: assets ?? DEMO_ASSETS, buoys: buoys ?? DEMO_BUOYS, sources: { zones: zones ? 'file' : 'demo', assets: assets ? 'file' : 'demo', buoys: buoys ? 'file' : 'demo' } }
  })()
  return localPromise
}
