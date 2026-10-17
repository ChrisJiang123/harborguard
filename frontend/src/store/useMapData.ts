import { create } from 'zustand'
import type { MapResources } from '../data/mapGeometry'
import { parseAssets, parseBuoys, parseZones } from '../data/mapGeometry'
import { fetchJSON, loadLocalData } from '../data/staticData'

interface MapDataStore { resources: MapResources | null; loading: boolean; error: string | null }
export const useMapData = create<MapDataStore>(() => ({ resources: null, loading: true, error: null }))
const API_BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000/api').replace(/\/$/, '')
let pending: Promise<void> | null = null

export function ensureMapData(force = false): Promise<void> {
  if (pending) return pending
  if (!force && useMapData.getState().resources) return Promise.resolve()
  useMapData.setState({ loading: true, error: null })
  pending = (async () => {
    try {
      const params = new URLSearchParams(location.search)
      const offline = params.get('mock') === '1' || params.has('replay')
      const local = loadLocalData(force)
      if (offline) {
        useMapData.setState({ resources: await local, loading: false })
        return
      }
      // API fetches happen once per session (or on an explicit retry), never per state tick.
      const result = await Promise.allSettled([
        fetchJSON(`${API_BASE}/zones`), fetchJSON(`${API_BASE}/assets`), fetchJSON(`${API_BASE}/buoys`),
      ])
      const fallback = await local
      const zones = result[0].status === 'fulfilled' ? parseZones(result[0].value) : null
      const assets = result[1].status === 'fulfilled' ? parseAssets(result[1].value) : null
      const buoys = result[2].status === 'fulfilled' ? parseBuoys(result[2].value) : null
      useMapData.setState({ loading: false, resources: { zones: zones ?? fallback.zones, assets: assets ?? fallback.assets, buoys: buoys ?? fallback.buoys, sources: { zones: zones ? 'api' : fallback.sources.zones, assets: assets ? 'api' : fallback.sources.assets, buoys: buoys ? 'api' : fallback.sources.buoys } } })
    } catch {
      useMapData.setState({ loading: false, error: 'Could not load layer data. Reload the layers.' })
    }
  })().finally(() => { pending = null })
  return pending
}
