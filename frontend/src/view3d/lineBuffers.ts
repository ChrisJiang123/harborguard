import type { Line2 } from 'three-stdlib'
import type { Point3 } from './coordinates'

/** Reuse Drei's existing interleaved attributes rather than allocating GPU buffers at 5 Hz. */
export function updateLine(line: Line2 | null, points: readonly Point3[]) {
  if (!line) return
  const geometry = line.geometry
  const start = geometry.getAttribute('instanceStart')
  const end = geometry.getAttribute('instanceEnd')
  const distanceStart = geometry.getAttribute('instanceDistanceStart')
  const distanceEnd = geometry.getAttribute('instanceDistanceEnd')
  if (!start || !end) return
  const count = Math.min(start.count, Math.max(0, points.length - 1))
  geometry.instanceCount = count
  let distance = 0
  for (let i = 0; i < count; i++) {
    const a = points[i]!, b = points[i + 1]!
    start.setXYZ(i, a[0], a[1], a[2]); end.setXYZ(i, b[0], b[1], b[2])
    distanceStart?.setX(i, distance)
    distance += Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2])
    distanceEnd?.setX(i, distance)
  }
  start.needsUpdate = true; end.needsUpdate = true
  if (distanceStart) distanceStart.needsUpdate = true
  if (distanceEnd) distanceEnd.needsUpdate = true
}
