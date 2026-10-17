import { useEffect, useMemo } from 'react'
import { useTexture } from '@react-three/drei'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute, SRGBColorSpace } from 'three'
import type { ShoreTerrainGrid } from '../data/shoreTerrain'
import { worldPosition } from './coordinates'

const COLOR_STOPS = [new Color('#c4b48e'), new Color('#a7a982'), new Color('#718c70'), new Color('#536f63'), new Color('#7c7669')]
const WHITE = new Color('#ffffff')
const BLACK = new Color('#000000')

function heightColor(height: number, minimum: number, maximum: number): Color {
  const p = Math.max(0, Math.min(1, (height - minimum) / Math.max(1, maximum - minimum)))
  const scaled = Math.pow(p, .46) * (COLOR_STOPS.length - 1)
  const index = Math.min(COLOR_STOPS.length - 2, Math.floor(scaled))
  return COLOR_STOPS[index]!.clone().lerp(COLOR_STOPS[index + 1]!, scaled - index).lerp(WHITE, .86)
}
export function CoastalTerrain3D({ grid, verticalScale }: { grid: ShoreTerrainGrid; verticalScale: number }) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry()
    const { width, height, bounds, nodata_value, min_elevation_m, max_elevation_m } = grid.metadata
    const positions: number[] = []
    const colors: number[] = []
    const uvs: number[] = []
    const indices: number[] = []
    for (let row = 0; row < height; row++) {
      const lat = bounds.north - row / (height - 1) * (bounds.north - bounds.south)
      for (let column = 0; column < width; column++) {
        const lon = bounds.west + column / (width - 1) * (bounds.east - bounds.west)
        const elevation = grid.values[row * width + column]!
        const valid = elevation !== nodata_value
        const point = worldPosition(lat, lon)
        positions.push(point[0], valid ? elevation : 0, point[2])
        uvs.push(column / (width - 1), 1 - row / (height - 1))
        const color = valid ? heightColor(elevation, min_elevation_m, max_elevation_m) : BLACK
        colors.push(color.r, color.g, color.b)
      }
    }
    for (let row = 0; row < height - 1; row++) {
      for (let column = 0; column < width - 1; column++) {
        const a = row * width + column, b = a + 1, c = a + width, d = c + 1
        if ([a, b, c, d].some(index => grid.values[index] === nodata_value)) continue
        indices.push(a, c, b, b, c, d)
      }
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setAttribute('uv', new Float32BufferAttribute(uvs, 2))
    result.setIndex(indices)
    result.computeVertexNormals()
    result.computeBoundingSphere()
    return result
  }, [grid])
  const sourceImagery = useTexture('/data/shore-ortho-usgs-naip.png')
  const imagery = useMemo(() => {
    const texture = sourceImagery.clone()
    texture.colorSpace = SRGBColorSpace
    texture.anisotropy = 8
    return texture
  }, [sourceImagery])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => imagery.dispose(), [imagery])
  return <mesh geometry={geometry} scale={[1, verticalScale, 1]} raycast={() => {}} receiveShadow><meshStandardMaterial map={imagery} vertexColors roughness={1} metalness={0} side={DoubleSide} /></mesh>
}
