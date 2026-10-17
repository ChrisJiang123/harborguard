import type { Track } from '../types/contract'
import { toLatLon, toLocal } from '../map2d/geo'

type XY = [number, number]
export type DemoVesselId = 'T3' | 'T4'
interface RouteSample { east: number; north: number; distance: number; speed: number; time: number }
interface VesselRoute { points: RouteSample[]; duration: number; offset: number }

// Hand-authored demonstration corridor, checked against the bundled NOAA water mask.
// Not AIS, an official traffic scheme, a clearance calculation, or an autonomous navigator.
export const DEMO_CHANNEL: [number, number][] = [
  [33.7160, -118.2702], [33.7190, -118.2665], [33.7213, -118.2636],
  [33.7255, -118.2620], [33.7298, -118.2588],
]
const length = (a: XY, b: XY) => Math.hypot(b[0] - a[0], b[1] - a[1])
const mix = (a: XY, b: XY, t: number): XY => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]

function makeRoute(reverse: boolean, cruise: number, offset: number): VesselRoute {
  const center = (reverse ? [...DEMO_CHANNEL].reverse() : DEMO_CHANNEL).map(([lat, lon]) => toLocal(lat, lon))
  // Opposing demo lanes are displaced 40 m to starboard, not a universal port rule.
  const lane = center.map((point, index): XY => {
    const previous = center[Math.max(0, index - 1)]!, next = center[Math.min(center.length - 1, index + 1)]!
    const distance = length(previous, next)
    return [point[0] + (next[1] - previous[1]) / distance * 40, point[1] - (next[0] - previous[0]) / distance * 40]
  })
  const path: XY[] = [lane[0]!]
  const straight = (end: XY) => {
    const start = path.at(-1)!, steps = Math.max(1, Math.ceil(length(start, end) / 2))
    for (let i = 1; i <= steps; i++) path.push(mix(start, end, i / steps))
  }
  for (let i = 1; i < lane.length - 1; i++) {
    const previous = lane[i - 1]!, corner = lane[i]!, next = lane[i + 1]!
    const cut = Math.min(100, length(previous, corner) * .25, length(corner, next) * .25)
    const entry = mix(corner, previous, cut / length(previous, corner))
    const exit = mix(corner, next, cut / length(corner, next))
    straight(entry)
    const steps = Math.max(12, Math.ceil(cut))
    for (let step = 1; step <= steps; step++) {
      const t = step / steps
      path.push(mix(mix(entry, corner, t), mix(corner, exit, t), t))
    }
  }
  straight(lane.at(-1)!)
  const points: RouteSample[] = path.map(([east, north], index) => {
    let limit = cruise
    if (index > 0 && index < path.length - 1) {
      const previous = path[index - 1]!, next = path[index + 1]!, point = path[index]!
      const a = [point[0] - previous[0], point[1] - previous[1]], b = [next[0] - point[0], next[1] - point[1]]
      const angle = Math.abs(Math.atan2(a[0]! * b[1]! - a[1]! * b[0]!, a[0]! * b[0]! + a[1]! * b[1]!))
      const curvature = angle / Math.max(.01, (length(previous, point) + length(point, next)) / 2)
      limit = Math.min(cruise, Math.sqrt(.03 / Math.max(curvature, 1e-8)))
    }
    return { east, north, distance: 0, speed: limit, time: 0 }
  })
  points[0]!.speed = Math.min(2.2, cruise)
  points.at(-1)!.speed = 0
  for (let i = 1; i < points.length; i++) {
    const previous = points[i - 1]!, point = points[i]!, distance = length(path[i - 1]!, path[i]!)
    point.distance = previous.distance + distance
    point.speed = Math.min(point.speed, Math.sqrt(previous.speed ** 2 + 2 * .035 * distance))
  }
  for (let i = points.length - 2; i >= 0; i--) {
    const point = points[i]!, next = points[i + 1]!
    point.speed = Math.min(point.speed, Math.sqrt(next.speed ** 2 + 2 * .045 * (next.distance - point.distance)))
  }
  for (let i = 1; i < points.length; i++) {
    const previous = points[i - 1]!, point = points[i]!
    point.time = previous.time + 2 * (point.distance - previous.distance) / (previous.speed + point.speed)
  }
  return { points, duration: points.at(-1)!.time, offset }
}

// Begin underway so the short demo includes the channel bend, not a sped-up voyage.
const routes: Record<DemoVesselId, VesselRoute> = { T3: makeRoute(false, 3.6, 200), T4: makeRoute(true, 3.8, 80) }
export const demoVesselDuration = (id: DemoVesselId) => routes[id].duration - routes[id].offset

export function sampleDemoVessel(id: DemoVesselId, t: number) {
  const route = routes[id], time = Math.max(0, Math.min(route.duration, t + route.offset))
  let lower = 0, upper = route.points.length - 1
  while (lower + 1 < upper) {
    const middle = (lower + upper) >>> 1
    if (route.points[middle]!.time <= time) lower = middle
    else upper = middle
  }
  const start = route.points[lower]!, end = route.points[upper]!
  const duration = end.time - start.time, elapsed = time - start.time
  const acceleration = (end.speed - start.speed) / duration
  const distance = end.distance - start.distance
  const traveled = Math.max(0, Math.min(distance, start.speed * elapsed + .5 * acceleration * elapsed ** 2))
  const east = (end.east - start.east) / distance, north = (end.north - start.north) / distance
  const speed = time >= route.duration ? 0 : Math.max(0, start.speed + acceleration * elapsed)
  const [lat, lon] = toLatLon(start.east + east * traveled, start.north + north * traveled)
  return { lat, lon, heading: (Math.atan2(east, north) * 180 / Math.PI + 360) % 360, speed, vel_e: east * speed, vel_n: north * speed }
}

export function demoVesselTrack(id: DemoVesselId, t: number): Track {
  const current = sampleDemoVessel(id, t)
  const count = Math.min(60, Math.floor(t / 2) + 1)
  const history: Track['history'] = Array.from({ length: count }, (_, index) => {
    const time = t - (count - 1 - index) * 2, position = sampleDemoVessel(id, time)
    return [position.lat, position.lon, 0, time]
  })
  return {
    id, status: 'confirmed', cls: 'vessel', conf: .99, cue: 'none', lat: current.lat, lon: current.lon, depth_m: 0,
    vel_e: current.vel_e, vel_n: current.vel_n, vel_d: 0, speed_mps: current.speed, heading_deg: current.heading,
    err: { a_m: 18, b_m: 8, angle_deg: current.heading }, history,
    predicted: Array.from({ length: 10 }, (_, index) => {
      const time = t + (index + 1) * 10, position = sampleDemoVessel(id, time)
      return [position.lat, position.lon, 0, time]
    }),
    level: 0, risk: .01, detection_id: null,
  }
}
