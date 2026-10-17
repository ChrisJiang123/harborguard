import type { Track } from '../types/contract'

export const ORIGIN = { lat: 33.7300, lon: -118.2600 } as const
export const PORT_CENTER: [number, number] = [33.735, -118.255]
const EAST_SCALE = 111320 * Math.cos(ORIGIN.lat * Math.PI / 180)
const NORTH_SCALE = 110540

/** Task-contract local metres: east is x, north is y. */
export function toLocal(lat: number, lon: number): [number, number] {
  return [(lon - ORIGIN.lon) * EAST_SCALE, (lat - ORIGIN.lat) * NORTH_SCALE]
}
export function toLatLon(east: number, north: number): [number, number] {
  return [ORIGIN.lat + north / NORTH_SCALE, ORIGIN.lon + east / EAST_SCALE]
}

export function errorEllipse(track: Pick<Track, 'lat' | 'lon' | 'err'>): [number, number][] {
  const [east, north] = toLocal(track.lat, track.lon)
  const rotation = track.err.angle_deg * Math.PI / 180
  // The contract gives a planar ellipse angle. Rotate in east/north metres, not degrees.
  return Array.from({ length: 36 }, (_, i) => {
    const theta = i / 36 * Math.PI * 2
    const x = track.err.a_m * Math.cos(theta)
    const y = track.err.b_m * Math.sin(theta)
    return toLatLon(east + x * Math.cos(rotation) - y * Math.sin(rotation), north + x * Math.sin(rotation) + y * Math.cos(rotation))
  })
}

export function trailPositions(points: Track['history']): [number, number][] {
  return points.filter(point => Number.isFinite(point[0]) && Number.isFinite(point[1])).map(point => [point[0], point[1]])
}
