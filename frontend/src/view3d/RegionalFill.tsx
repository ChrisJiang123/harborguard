import { useEffect, useMemo } from 'react'
import { BufferGeometry, Color, Float32BufferAttribute } from 'three'
import type { BathymetryBounds, BathymetryGrid } from '../data/bathymetry'
import { regionalMeshData } from './regionalMesh'
import { stitchedHeightfieldNormals } from './heightfield'
import { stitchTerrainBoundary } from './stitchTerrain'
import { terrainMaterial } from './terrainMaterial'
import type { TerrainEffects } from './terrainMaterial'

/** Draw only cells that H12617 does not support with four valid corners.
 * Both grids share the same lattice. Boundary positions match measured vertices
 * exactly; all feathering lives in the separate regional preprocessing product.
 */
export function RegionalFill({ grid, survey, verticalScale, effects, excludeBounds, stitchTo }: { grid: BathymetryGrid; survey: BathymetryGrid; verticalScale: number; effects: TerrainEffects; excludeBounds?: BathymetryBounds; stitchTo?: BathymetryGrid }) {
  const geometry = useMemo(() => {
    const base = regionalMeshData(grid, survey, excludeBounds)
    const data = stitchTo ? stitchTerrainBoundary(base, grid, stitchTo) : base
    const { width, height } = survey.metadata
    const result = new BufferGeometry()
    result.setAttribute('position', new Float32BufferAttribute(data.positions, 3))
    const heights = data.depths.map(v => -v)
    result.setAttribute('normal', new Float32BufferAttribute(stitchedHeightfieldNormals(heights, width, height, grid.metadata.approximate_spacing_m.east_west, grid.metadata.approximate_spacing_m.north_south, data.positions, stitchTo), 3))
    const shallow = new Color('#669c99'), deep = new Color('#173c5a'), color = new Color()
    const colors = new Float32Array(heights.length*3)
    for (let i = 0; i < heights.length; i++) {
      color.copy(shallow).lerp(deep, Number.isFinite(heights[i]) ? Math.min(1, Math.max(0, -heights[i]!/35)) : 1)
      colors.set([color.r, color.g, color.b], i*3)
    }
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setIndex(data.indices)
    result.computeBoundingSphere()
    return result
  }, [grid, survey, excludeBounds, stitchTo])
  const material = useMemo(() => terrainMaterial(effects, true), [effects])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => material.dispose(), [material])
  return <mesh geometry={geometry} material={material} scale={[1, verticalScale, 1]} raycast={() => {}} />
}
