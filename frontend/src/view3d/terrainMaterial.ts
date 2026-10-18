import { MeshStandardMaterial } from 'three'

export interface TerrainEffects { detail: boolean; shoreline: boolean; caustics: boolean }
export const DEFAULT_TERRAIN_EFFECTS: TerrainEffects = { detail: true, shoreline: true, caustics: false }

/** Procedural normal/colour effects change lighting only, never survey geometry.
 * All sand ripples, wet-sand bands and caustics are illustrative, not observations.
 */
export function terrainMaterial(effects: TerrainEffects, regional = false) {
  const material = new MeshStandardMaterial({ vertexColors: true, roughness: .94, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 })
  material.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vTerrainLocal;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvTerrainLocal = position;')
    shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vTerrainLocal;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        ${effects.detail ? `float footprint = max(length(dFdx(vTerrainLocal.xz)), length(dFdy(vTerrainLocal.xz)));
        float detailLod = 1.0 - smoothstep(1.0, 6.0, footprint);
        float ripple = sin(vTerrainLocal.x * 1.2 + sin(vTerrainLocal.z * .15));
        normal = normalize(normal + vec3(ripple, 0.0, ripple*.35) * .055 * detailLod);` : ''}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        ${effects.shoreline ? `float wetBand = 1.0 - smoothstep(.3, 2.4, abs(vTerrainLocal.y));
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.27,.25,.17), wetBand*.55);` : ''}
        ${regional ? `// Derivative-filtered hatch explicitly distinguishes regional interpolation.
        float diagonal = (vTerrainLocal.x + vTerrainLocal.z) * .22;
        float aa = max(fwidth(diagonal), .02);
        float hatch = 1.0-smoothstep(.09, .09+aa, abs(fract(diagonal)-.5));
        float grey = dot(diffuseColor.rgb, vec3(.2126,.7152,.0722));
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(grey), .5) * (1.0-hatch*.12);` : ''}
        ${effects.caustics ? `float wave = sin(vTerrainLocal.x*.43 + sin(vTerrainLocal.z*.31));
        diffuseColor.rgb *= 1.0 + pow(max(0.0, wave), 12.0)*.12*exp(min(0.0,vTerrainLocal.y)*.04);` : ''}`)
  }
  material.customProgramCacheKey = () => JSON.stringify([effects, regional])
  return material
}
