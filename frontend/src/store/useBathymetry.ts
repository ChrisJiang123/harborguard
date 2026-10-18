import { create } from 'zustand'
import { compatibleBathymetryDetail, fetchBathymetry } from '../data/bathymetry'
import type { BathymetryGrid } from '../data/bathymetry'

interface BathymetryStore { grid: BathymetryGrid | null; detailGrid: BathymetryGrid | null; fillGrid: BathymetryGrid | null; fillError: string | null; detailError: string | null; loading: boolean; error: string | null; url: string | null }
export const useBathymetry = create<BathymetryStore>(() => ({ grid: null, detailGrid: null, fillGrid: null, fillError: null, detailError: null, loading: true, error: null, url: null }))
const configuredUrl = import.meta.env.VITE_BATHYMETRY_URL || '/data/seabed-dem.json'
let pending: Promise<void> | null = null

export function ensureBathymetry(force = false): Promise<void> {
  if (pending) return pending
  if (!force && useBathymetry.getState().grid) return Promise.resolve()
  useBathymetry.setState({ loading: true, error: null })
  pending = Promise.allSettled([fetchBathymetry(configuredUrl), configuredUrl === '/data/seabed-dem.json' ? fetchBathymetry('/data/seabed-detail-mb.json') : Promise.resolve(null), configuredUrl === '/data/seabed-dem.json' ? fetchBathymetry('/data/seabed-fill-regional.json', 15000) : Promise.resolve(null)]).then(([main, detail, fill]) => {
    if (main.status === 'rejected') throw main.reason
    const patch = detail.status === 'fulfilled' ? detail.value : null
    const compatible = patch && compatibleBathymetryDetail(main.value, patch)
    const regional = fill.status === 'fulfilled' ? fill.value : null
    const a = main.value.metadata, b = regional?.metadata
    const aligned = regional && b?.source_kind === 'regional_dem' && b.width === a.width && b.height === a.height && ['west','east','north','south'].every(key => Math.abs(a.bounds[key as keyof typeof a.bounds]-b.bounds[key as keyof typeof a.bounds]) < 1e-9) && main.value.values.every((value,i) => value === a.nodata_value || Math.abs(value-regional.values[i]!) < .00001)
    useBathymetry.setState({ grid: main.value, detailGrid: compatible ? patch : null, fillGrid: aligned ? regional : null, fillError: fill.status === 'rejected' ? 'Regional fill unavailable; unsurveyed gaps remain visible.' : regional && !aligned ? 'Regional fill/survey grid mismatch; fill disabled.' : null, detailError: detail.status === 'rejected' ? 'High-resolution multibeam patch unavailable; showing harbor grid only.' : patch && !compatible ? 'Detail source/datum/grid mismatch; patch disabled.' : null, loading: false, error: null, url: configuredUrl })
  }).catch(error => useBathymetry.setState({ grid: null, detailGrid: null, fillGrid: null, fillError: null, detailError: null, loading: false, error: error instanceof Error ? error.message : 'DEM request failed', url: configuredUrl })).finally(() => { pending = null })
  return pending
}
