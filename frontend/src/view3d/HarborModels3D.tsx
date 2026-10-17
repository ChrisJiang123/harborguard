import { useEffect, useMemo, useState } from 'react'
import { BufferGeometry, Color, ExtrudeGeometry, Float32BufferAttribute, Path, Shape, Vector2 } from 'three'
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js'
import { loadLocalBase, loadPortBuildings } from '../data/localBase'
import type { LocalBase } from '../data/localBase'
import { loadShoreTerrain, sampleShoreElevation } from '../data/shoreTerrain'
import type { ShoreTerrainGrid } from '../data/shoreTerrain'
import { worldPosition } from './coordinates'
import { CoastalTerrain3D } from './CoastalTerrain3D'

function PortLines({ data }: { data: LocalBase }) {
  const geometry = useMemo(() => {
    const positions: number[] = []
    const colors: number[] = []
    data.features.filter(feature => feature.geometry.type === 'LineString' && ['coastline', 'breakwater', 'pier', 'road'].includes(feature.properties.kind)).forEach(feature => {
      if (feature.geometry.type !== 'LineString') return
      const color = new Color(feature.properties.kind === 'road' ? '#75828a' : '#dde6ea')
      for (let i = 1; i < feature.geometry.coordinates.length; i++) {
        const previous = feature.geometry.coordinates[i - 1]!, current = feature.geometry.coordinates[i]!
        const a = worldPosition(previous[1]!, previous[0]!), b = worldPosition(current[1]!, current[0]!)
        positions.push(a[0], 2.4, a[2], b[0], 2.4, b[2])
        colors.push(color.r, color.g, color.b, color.r, color.g, color.b)
      }
    })
    const result = new BufferGeometry()
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    return result
  }, [data])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <lineSegments geometry={geometry} raycast={() => {}}><lineBasicMaterial vertexColors transparent opacity={.82} /></lineSegments>
}

function PortBuildings({ data, verticalScale, terrain }: { data: LocalBase; verticalScale: number; terrain: ShoreTerrainGrid | null }) {
  const geometry = useMemo(() => {
    const pieces: ExtrudeGeometry[] = []
    for (const feature of data.features) {
      if (feature.properties.kind !== 'building' || feature.geometry.type !== 'Polygon') continue
      const rings = feature.geometry.coordinates
      if (!rings.length || rings[0]!.length < 4) continue
      const toPoints = (ring: number[][]) => ring.map(([lon, lat]) => {
        const point = worldPosition(lat!, lon!)
        return new Vector2(point[0], -point[2])
      })
      const outer = toPoints(rings[0]!)
      const shape = new Shape(outer)
      shape.holes = rings.slice(1).filter(ring => ring.length >= 4).map(ring => new Path(toPoints(ring)))
      const height = Math.min(100, Math.max(2, feature.properties.height_m ?? 8)) * verticalScale
      const piece = new ExtrudeGeometry(shape, { depth: height, bevelEnabled: false, curveSegments: 1 })
      const anchor = rings[0]![0]!
      const ground = terrain ? sampleShoreElevation(terrain, anchor[1]!, anchor[0]!) ?? 0 : 0
      piece.translate(0, 0, ground * verticalScale)
      pieces.push(piece)
    }
    const merged = pieces.length ? mergeGeometries(pieces, false) : null
    for (const piece of pieces) piece.dispose()
    const result = merged ?? new BufferGeometry()
    result.computeBoundingSphere()
    return result
  }, [data, terrain, verticalScale])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} raycast={() => {}}><meshStandardMaterial color="#cdd7dc" roughness={.9} metalness={.04} flatShading /></mesh>
}

export function HarborModels3D({ verticalScale, onStatus }: { verticalScale: number; onStatus: (status: string) => void }) {
  const [base, setBase] = useState<LocalBase | null>(null)
  const [buildings, setBuildings] = useState<LocalBase | null>(null)
  const [terrain, setTerrain] = useState<ShoreTerrainGrid | null>(null)
  useEffect(() => {
    let active = true
    void Promise.allSettled([loadLocalBase(), loadPortBuildings(), loadShoreTerrain()]).then(([baseResult, buildingResult, terrainResult]) => {
      if (!active) return
      if (baseResult.status === 'fulfilled') setBase(baseResult.value)
      if (buildingResult.status === 'fulfilled') setBuildings(buildingResult.value)
      if (terrainResult.status === 'fulfilled') setTerrain(terrainResult.value)
      const lineCount = baseResult.status === 'fulfilled' ? baseResult.value.features.length : 0
      const buildingCount = buildingResult.status === 'fulfilled' ? buildingResult.value.features.filter(feature => feature.properties.kind === 'building').length : 0
      const warnings = [baseResult.status === 'rejected' ? 'OSM 岸线未加载' : '', buildingResult.status === 'rejected' ? '县级建筑轮廓未加载' : '', terrainResult.status === 'rejected' ? 'USGS 实测岸上 DEM 未加载' : ''].filter(Boolean)
      onStatus(`OSM 岸线/码头 ${lineCount} 条 · LA County 建筑 ${buildingCount} 栋 · USGS 3DEP 岸上地形 ${terrainResult.status === 'fulfilled' ? `${terrainResult.value.metadata.width}×${terrainResult.value.metadata.height} NAVD88 DEM + USGS/USDA NAIP 正射影像` : '不可用'}${warnings.length ? ` · ${warnings.join(' / ')}` : ''}`)
    })
    return () => { active = false }
  }, [onStatus])
  return <group>
    {base && <PortLines data={base} />}
    {terrain && <CoastalTerrain3D grid={terrain} verticalScale={verticalScale} />}
    {buildings && <PortBuildings data={buildings} verticalScale={verticalScale} terrain={terrain} />}
  </group>
}
