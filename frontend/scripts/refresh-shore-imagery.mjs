import { readFile, writeFile } from 'node:fs/promises'

// Refresh imagery only: never replace or resample the underlying elevation grid.
const metadataUrl = new URL('../public/data/shore-dem-usgs-3dep.json', import.meta.url)
const terrain = JSON.parse(await readFile(metadataUrl, 'utf8'))
const { west, south, east, north } = terrain.metadata.bounds
const width = 3072, height = 1668
const endpoint = 'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer'
const url = new URL(`${endpoint}/exportImage`)
url.search = new URLSearchParams({ bbox: `${west},${south},${east},${north}`, bboxSR: '4326', imageSR: '4326', size: `${width},${height}`, format: 'png32', interpolation: 'RSP_Bilinear', f: 'image', adjustAspectRatio: 'false' }).toString()
const response = await fetch(url, { signal: AbortSignal.timeout(60000) })
if (!response.ok) throw new Error(`USGS imagery export failed: HTTP ${response.status}`)
const bytes = Buffer.from(await response.arrayBuffer())
if (bytes.length < 1000 || bytes.length > 32_000_000 || !bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) || bytes.readUInt32BE(16) !== width || bytes.readUInt32BE(20) !== height) throw new Error('USGS did not return the requested bounded PNG; existing snapshot retained')
terrain.metadata.imagery_grid = `${width}×${height} RGB orthophoto, same EPSG:4326 bounds as terrain. Display pixels are not a claim of source ground accuracy.`
terrain.metadata.imagery_export_url = url.toString()
terrain.metadata.imagery_retrieved_at = new Date().toISOString()
await writeFile(new URL('../public/data/shore-ortho-usgs-naip.png', import.meta.url), bytes)
await writeFile(metadataUrl, `${JSON.stringify(terrain)}\n`)
console.log(`Saved ${width}×${height} USGS/USDA NAIP orthophoto (${bytes.length.toLocaleString()} bytes); DEM unchanged.`)
