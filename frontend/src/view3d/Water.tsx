import { useEffect, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { BufferGeometry, DoubleSide, Float32BufferAttribute, MeshStandardMaterial } from 'three'
import type { BathymetryGrid } from '../data/bathymetry'
import type { SceneBounds } from './coordinates'
import { buildWaterSurfaceData } from './waterMask'

function buildWaterMask(grid: BathymetryGrid) {
  const { positions, indices } = buildWaterSurfaceData(grid)
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}

export function Water({ bounds, opacity, grid, surfaceEffects = true }: { bounds: SceneBounds; opacity: number; grid: BathymetryGrid | null; surfaceEffects?: boolean }) {
  const mask = useMemo(() => grid && grid.metadata.source_kind !== 'synthetic' ? buildWaterMask(grid) : null, [grid])
  useEffect(() => () => mask?.dispose(), [mask])
  const time = useMemo(() => ({ value: 0 }), [])
  const material = useMemo(() => {
    const result = new MeshStandardMaterial({ color: '#1680a0', transparent: true, opacity, roughness: .42, metalness: .08, depthWrite: false, side: DoubleSide, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 })
    if (surfaceEffects) result.onBeforeCompile = shader => {
      shader.uniforms.waterTime = time
      shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWaterWorld;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWaterWorld = (modelMatrix*vec4(position,1.0)).xyz;')
      shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWaterWorld; uniform float waterTime;')
        .replace('#include <opaque_fragment>', `
          vec3 waterNormal = normalize(vec3(.025*sin(vWaterWorld.x*.08+waterTime*.35), 1.0, .025*cos(vWaterWorld.z*.06+waterTime*.3)));
          float facing = abs(dot(normalize(cameraPosition-vWaterWorld),waterNormal));
          float fresnel = .02+.98*pow(1.0-facing,5.0);
          bool below = cameraPosition.y < 0.0;
          // Schlick + critical angle (water/air n=1.333): total internal reflection
          // from below. Illustrative interface; no claim of measured waves/reflection.
          if (below) fresnel = mix(fresnel,1.0,1.0-smoothstep(.64,.69,facing));
          outgoingLight = mix(outgoingLight, below ? vec3(.10,.29,.34) : vec3(.40,.61,.69), fresnel*.65);
          diffuseColor.a = clamp(opacity*(below ? .65 : .85)+fresnel*.22,0.0,.8);
          #include <opaque_fragment>`)
    }
    result.customProgramCacheKey = () => String(surfaceEffects)
    return result
  }, [opacity, surfaceEffects, time])
  useEffect(() => () => material.dispose(), [material])
  // Three shader uniform: mutable GPU state, intentionally outside React state.
  // eslint-disable-next-line react/immutability
  useFrame(({ clock }) => { time.value = clock.elapsedTime })
  const size = Math.max(8000, bounds.span * 2.2)
  return mask
    ? <mesh geometry={mask} material={material} position={[0, .02, 0]} renderOrder={2} raycast={() => {}} />
    : <group position={[bounds.center[0], 0, bounds.center[2]]}><mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} raycast={() => {}}><planeGeometry args={[size, size]} /><meshStandardMaterial color="#1680b2" transparent opacity={opacity} roughness={.45} metalness={.08} depthWrite={false} side={DoubleSide} /></mesh><gridHelper args={[size, 32, '#65b9d6', '#24536c']} position={[0, .3, 0]} raycast={() => {}} /></group>
}
