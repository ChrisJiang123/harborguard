import { create } from 'zustand'
import { fetchBathymetry } from '../data/bathymetry'
import type { BathymetryGrid } from '../data/bathymetry'

interface BathymetryStore { grid: BathymetryGrid | null; loading: boolean; error: string | null; url: string | null }
export const useBathymetry = create<BathymetryStore>(() => ({ grid: null, loading: true, error: null, url: null }))
const configuredUrl = import.meta.env.VITE_BATHYMETRY_URL || '/data/seabed-dem.json'
let pending: Promise<void> | null = null

export function ensureBathymetry(force = false): Promise<void> {
  if (pending) return pending
  if (!force && useBathymetry.getState().grid) return Promise.resolve()
  useBathymetry.setState({ loading: true, error: null })
  pending = fetchBathymetry(configuredUrl).then(grid => useBathymetry.setState({ grid, loading: false, error: null, url: configuredUrl })).catch(error => useBathymetry.setState({ grid: null, loading: false, error: error instanceof Error ? error.message : 'DEM 读取失败', url: configuredUrl })).finally(() => { pending = null })
  return pending
}
