import { create } from 'zustand'
import { compatibleBathymetryDetail, fetchBathymetry } from '../data/bathymetry'
import type { BathymetryGrid } from '../data/bathymetry'

interface BathymetryStore { grid: BathymetryGrid | null; detailGrid: BathymetryGrid | null; detailError: string | null; loading: boolean; error: string | null; url: string | null }
export const useBathymetry = create<BathymetryStore>(() => ({ grid: null, detailGrid: null, detailError: null, loading: true, error: null, url: null }))
const configuredUrl = import.meta.env.VITE_BATHYMETRY_URL || '/data/seabed-dem.json'
let pending: Promise<void> | null = null

export function ensureBathymetry(force = false): Promise<void> {
  if (pending) return pending
  if (!force && useBathymetry.getState().grid) return Promise.resolve()
  useBathymetry.setState({ loading: true, error: null })
  pending = Promise.allSettled([fetchBathymetry(configuredUrl), configuredUrl === '/data/seabed-dem.json' ? fetchBathymetry('/data/seabed-detail-mb.json') : Promise.resolve(null)]).then(([main, detail]) => {
    if (main.status === 'rejected') throw main.reason
    const patch = detail.status === 'fulfilled' ? detail.value : null
    const compatible = patch && compatibleBathymetryDetail(main.value, patch)
    useBathymetry.setState({ grid: main.value, detailGrid: compatible ? patch : null, detailError: detail.status === 'rejected' ? 'High-resolution multibeam patch unavailable; showing harbor grid only.' : patch && !compatible ? 'Detail source/datum/grid mismatch; patch disabled.' : null, loading: false, error: null, url: configuredUrl })
  }).catch(error => useBathymetry.setState({ grid: null, detailGrid: null, detailError: null, loading: false, error: error instanceof Error ? error.message : 'DEM request failed', url: configuredUrl })).finally(() => { pending = null })
  return pending
}
