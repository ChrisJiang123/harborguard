/** Display-only contour reconstruction of a raster land mask. No source heights
 * or survey samples are changed. Tolerance is bounded in metres, not pixels.
 * The same displaced vertices feed the land top and illustrative quay panels.
 */
export function coastalBoundary(positions: Float32Array, valid: Uint8Array, width: number, height: number, tolerance: number) {
  const cells = new Uint8Array((width - 1) * (height - 1))
  const cell = (r: number, c: number) => r >= 0 && c >= 0 && r < height - 1 && c < width - 1 && cells[r * (width - 1) + c] === 1
  for (let r = 0; r < height - 1; r++) for (let c = 0; c < width - 1; c++) {
    const a = r * width + c
    if (valid[a] && valid[a + 1] && valid[a + width] && valid[a + width + 1]) cells[r * (width - 1) + c] = 1
  }
  const edges: [number, number][] = []
  for (let r = 0; r < height - 1; r++) for (let c = 0; c < width - 1; c++) {
    if (!cell(r, c)) continue
    const a = r * width + c, b = a + 1, d = a + width + 1, e = a + width
    if (!cell(r - 1, c)) edges.push([b, a])
    if (!cell(r + 1, c)) edges.push([e, d])
    if (!cell(r, c - 1)) edges.push([a, e])
    if (!cell(r, c + 1)) edges.push([d, b])
  }
  if (tolerance <= 0) return edges
  const next = new Map<number, number[]>()
  edges.forEach(([a], i) => { const list = next.get(a) ?? []; list.push(i); next.set(a, list) })
  const visited = new Uint8Array(edges.length)
  const pinned = new Uint8Array(valid.length)
  const offsetX = new Float32Array(valid.length), offsetZ = new Float32Array(valid.length)
  const boundary = new Set<number>()
  const project = (i: number, a: number, b: number) => {
    const x = positions[i * 3]!, z = positions[i * 3 + 2]!, ax = positions[a * 3]!, az = positions[a * 3 + 2]!
    const dx = positions[b * 3]! - ax, dz = positions[b * 3 + 2]! - az
    const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / Math.max(1e-12, dx * dx + dz * dz)))
    return [ax + dx * t - x, az + dz * t - z] as const
  }
  for (let first = 0; first < edges.length; first++) {
    if (visited[first]) continue
    const loop: number[] = [], start = edges[first]![0]
    let current = first
    while (!visited[current]) {
      visited[current] = 1
      const [a, b] = edges[current]!
      loop.push(a); boundary.add(a); pinned[a] = 1
      if (b === start) { loop.push(b); break }
      const following = next.get(b)?.find(i => !visited[i])
      if (following === undefined) { loop.push(b); break }
      current = following
    }
    // Preserve small islands, crop boundaries and ambiguous point contacts.
    // Split closed rings opposite the start so RDP has a nonzero baseline.
    if (loop.length < 8) continue
    const keep = new Set<number>([0, loop.length - 1])
    let opposite = 0, farthest = 0
    for (let k = 0; k < loop.length; k++) {
      const i = loop[k]!, dx = positions[i * 3]! - positions[start * 3]!, dz = positions[i * 3 + 2]! - positions[start * 3 + 2]!
      if (dx * dx + dz * dz > farthest) { farthest = dx * dx + dz * dz; opposite = k }
      const r = Math.floor(i / width), c = i % width
      if (r === 0 || c === 0 || r === height - 1 || c === width - 1 || (next.get(i)?.length ?? 0) !== 1) keep.add(k)
    }
    keep.add(opposite)
    const anchors = [...keep].sort((a, b) => a - b), stack: [number, number][] = []
    for (let k = 1; k < anchors.length; k++) stack.push([anchors[k - 1]!, anchors[k]!])
    while (stack.length) {
      const [a, b] = stack.pop()!
      let split = -1, error = tolerance * tolerance
      for (let k = a + 1; k < b; k++) {
        const [dx, dz] = project(loop[k]!, loop[a]!, loop[b]!)
        if (dx * dx + dz * dz > error) { split = k; error = dx * dx + dz * dz }
      }
      if (split >= 0) { keep.add(split); stack.push([a, split], [split, b]) }
    }
    const corners = [...keep].sort((a, b) => a - b)
    for (let k = 1; k < corners.length; k++) {
      const a = corners[k - 1]!, b = corners[k]!
      for (let n = a + 1; n < b; n++) {
        const i = loop[n]!, [dx, dz] = project(i, loop[a]!, loop[b]!)
        offsetX[i] = dx; offsetZ[i] = dz
      }
    }
  }
  // Harmonic displacement in a narrow land-side band prevents a straightened
  // contour from simply folding the first row of regular grid triangles.
  const distance = new Uint8Array(valid.length).fill(255), band: number[] = [...boundary]
  band.forEach(i => { distance[i] = 0 })
  const neighbors = (i: number) => [i % width > 0 ? i - 1 : -1, i % width + 1 < width ? i + 1 : -1, i >= width ? i - width : -1, i + width < valid.length ? i + width : -1]
  for (let k = 0; k < band.length; k++) {
    const i = band[k]!
    if (distance[i]! >= 8) continue
    for (const j of neighbors(i)) if (j >= 0 && valid[j] && distance[j] === 255) {
      distance[j] = distance[i]! + 1; band.push(j)
    }
  }
  for (let iteration = 0; iteration < 32; iteration++) for (const i of band) {
    if (pinned[i] || distance[i] === 8) continue
    let x = 0, z = 0, count = 0
    for (const j of neighbors(i)) if (j >= 0 && valid[j]) { x += offsetX[j]!; z += offsetZ[j]!; count++ }
    if (count) { offsetX[i] = x / count; offsetZ[i] = z / count }
  }
  const original = positions.slice()
  const area = (a: number, b: number, c: number) => (positions[b*3]!-positions[a*3]!)*(positions[c*3+2]!-positions[a*3+2]!) - (positions[b*3+2]!-positions[a*3+2]!)*(positions[c*3]!-positions[a*3]!)
  const unfolded = (i: number) => {
    const row = Math.floor(i / width), col = i % width
    for (let r = row - 1; r <= row; r++) for (let c = col - 1; c <= col; c++) {
      if (!cell(r, c)) continue
      const a = r * width + c, b = a + 1, e = a + width, d = e + 1
      if (area(a,b,e) < 1e-5 || area(b,d,e) < 1e-5) return false
    }
    return true
  }
  // A bounded simplification can collapse a thin spit or invert its adjacent
  // triangles. Apply it with a local orientation constraint: keep narrow
  // features wherever the existing topology cannot safely follow the contour.
  for (let pass = 0; pass < 8; pass++) for (let k = band.length - 1; k >= 0; k--) {
    const i = band[k]!, x = positions[i*3]!, z = positions[i*3+2]!
    const dx = original[i*3]! + offsetX[i]! - x, dz = original[i*3+2]! + offsetZ[i]! - z
    if (Math.abs(dx)+Math.abs(dz) < .0001) continue
    let accepted = false
    for (let factor = 1; factor >= 1/64; factor /= 2) {
      positions[i*3] = x + dx * factor; positions[i*3+2] = z + dz * factor
      if (unfolded(i)) { accepted = true; break }
    }
    if (!accepted) { positions[i*3] = x; positions[i*3+2] = z }
  }
  return edges
}
