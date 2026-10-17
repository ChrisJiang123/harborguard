import type { MapResources } from '../data/mapGeometry'
import type { BathymetryGrid } from '../data/bathymetry'
import type { Track } from '../types/contract'
import { toLocal } from '../map2d/geo'
import { SEABED_DEPTH_M, VZ } from '../theme'

export type Point3 = [number, number, number]
export type CameraMode = 'overview' | 'surface' | 'underwater' | 'follow' | 'dock'
export interface SceneBounds { center: Point3; span: number; width: number; length: number }
export const HISTORY_CAPACITY = 60
export const PREDICTED_CAPACITY = 12
export const FLIGHT_SECONDS = 1.5

export function worldPosition(lat: number, lon: number, depth = 0, verticalScale = VZ): Point3 {
  const [east, north] = toLocal(lat, lon)
  return [east, -depth * verticalScale, -north]
}

export function zoneRings(feature: MapResources['zones']['features'][number]): Point3[][] {
  const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates
  return polygons.flatMap(polygon => polygon.map(ring => ring.map(point => {
    const position = worldPosition(point[1]!, point[0]!)
    position[1] = 2
    return position
  })))
}

export function zoneCenter(feature: MapResources['zones']['features'][number], height = 3): Point3 {
  const exterior = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates[0]] : feature.geometry.coordinates.map(polygon => polygon[0])
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
  exterior.forEach(ring => ring?.forEach(point => {
    const [x, , z] = worldPosition(point[1]!, point[0]!)
    minX = Math.min(minX, x); maxX = Math.max(maxX, x)
    minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z)
  }))
  return Number.isFinite(minX) ? [(minX + maxX) / 2, height, (minZ + maxZ) / 2] : [0, height, 0]
}

export function zoneExtent(feature: MapResources['zones']['features'][number]): { width: number; length: number } {
  const rings = zoneRings(feature)
  let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity
  rings.forEach(ring => ring.forEach(([x, , z]) => {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x)
    minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z)
  }))
  return Number.isFinite(minX) ? { width: Math.max(30, maxX - minX), length: Math.max(30, maxZ - minZ) } : { width: 80, length: 120 }
}

export function sceneBounds(resources: MapResources | null, bathymetry?: BathymetryGrid | null): SceneBounds {
  let minX = -1800, maxX = 1800, minZ = -1800, maxZ = 1800
  function include(x: number, z: number, radius = 0) { minX = Math.min(minX, x - radius); maxX = Math.max(maxX, x + radius); minZ = Math.min(minZ, z - radius); maxZ = Math.max(maxZ, z + radius) }
  resources?.zones.features.forEach(feature => zoneRings(feature).forEach(ring => ring.forEach(point => include(point[0], point[2]))))
  resources?.assets.forEach(asset => { const position = worldPosition(asset.lat, asset.lon); include(position[0], position[2], Math.max(...asset.rings_m)) })
  resources?.buoys.forEach(buoy => { const position = worldPosition(buoy.lat, buoy.lon); include(position[0], position[2], buoy.range_m) })
  if (bathymetry) {
    const { west, south, east, north } = bathymetry.metadata.bounds
    for (const [lat, lon] of [[south, west], [south, east], [north, west], [north, east]]) {
      const position = worldPosition(lat!, lon!)
      include(position[0], position[2])
    }
  }
  return { center: [(minX + maxX) / 2, -SEABED_DEPTH_M / 3, (minZ + maxZ) / 2], span: Math.max(maxX - minX, maxZ - minZ), width: maxX - minX, length: maxZ - minZ }
}

export function cameraPreset(mode: CameraMode, bounds: SceneBounds, selected?: Pick<Track, 'lat' | 'lon' | 'depth_m'>, asset?: { lat: number; lon: number }, verticalScale = VZ): { position: Point3; target: Point3 } {
  if (mode === 'follow' && selected) {
    const target = worldPosition(selected.lat, selected.lon, selected.depth_m, verticalScale)
    return { target, position: [target[0] + 230, target[1] + 150, target[2] + 330] }
  }
  if (mode === 'dock' && asset) {
    const target = worldPosition(asset.lat, asset.lon, 2, verticalScale)
    return { target, position: [target[0] + 650, 280, target[2] + 850] }
  }
  if (mode === 'surface') {
    const target: Point3 = [bounds.center[0], 0, bounds.center[2]]
    return { target, position: [target[0] + bounds.span * .27, Math.max(260, bounds.span * .13), target[2] + bounds.span * .52] }
  }
  if (mode === 'underwater') {
    const target: Point3 = [bounds.center[0], -10 * verticalScale, bounds.center[2]]
    return { target, position: [target[0] + bounds.span * .14, -1 * verticalScale, target[2] + bounds.span * .22] }
  }
  const target: Point3 = [bounds.center[0], -8 * verticalScale, bounds.center[2]]
  return { target, position: [bounds.center[0] + bounds.span * .3, bounds.span * .72, bounds.center[2] + bounds.span * .62] }
}

export function seabedElevation(x: number, z: number): number {
  const undulation = (Math.sin(x / 700) * Math.cos(z / 900) + .5 * Math.sin((x + z) / 1000)) / 1.5 * 2
  return (-SEABED_DEPTH_M + undulation) * VZ
}

export function smoothFlight(progress: number): number {
  const p = Math.max(0, Math.min(1, progress))
  return p * p * (3 - 2 * p)
}

export function pingEnvelope(age: number, range: number): { radius: number; opacity: number } {
  const p = Math.max(0, Math.min(1, age / 1.5))
  return { radius: 5 + p * Math.max(0, range - 5), opacity: age < 0 || age >= 1.5 ? 0 : (1 - p) * .45 }
}

/** Update one reused point array. Motion is presentational, never predictive logic. */
export interface TrackMotion { track?: Track; verticalScale: number; from: Point3; to: Point3; current: Point3; changedAt: number }
export function createTrackMotion(track?: Track, verticalScale = VZ): TrackMotion {
  const position = track ? worldPosition(track.lat, track.lon, track.depth_m, verticalScale) : [0, 0, 0] as Point3
  return { track, verticalScale, from: [...position], to: [...position], current: [...position], changedAt: 0 }
}
export function sampleTrackMotion(motion: TrackMotion, track: Track, now: number, verticalScale = VZ): Point3 {
  const progress = Math.max(0, Math.min(1, (now - motion.changedAt) / .2))
  for (let i = 0; i < 3; i++) motion.current[i] = motion.from[i]! + (motion.to[i]! - motion.from[i]!) * progress
  if (motion.track !== track || motion.verticalScale !== verticalScale) {
    const point = worldPosition(track.lat, track.lon, track.depth_m, verticalScale)
    if (!motion.track) { motion.current.splice(0, 3, ...point) }
    motion.from.splice(0, 3, ...motion.current)
    motion.to.splice(0, 3, ...point)
    motion.changedAt = now
    motion.track = track
    motion.verticalScale = verticalScale
  }
  return motion.current
}
