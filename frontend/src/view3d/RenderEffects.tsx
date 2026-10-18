/* Three.js owns these mutable GPU resources. Per-frame updates intentionally
 * bypass React; they must not trigger a scene render on each state snapshot. */
/* eslint-disable react/immutability */
import { useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Color, FogExp2, WebGLRenderTarget } from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js'

/** Multisampled scene target + FXAA for silhouettes, thin contours and textures.
 * R3F's antialiased default framebuffer alone does not AA offscreen passes.
 */
export function RenderEffects({ antialias, scattering, verticalScale, span }: { antialias: boolean; scattering: boolean; verticalScale: number; span: number }) {
  const { gl, scene, camera, size } = useThree()
  const lastSize = useRef('')
  const effects = useMemo(() => {
    const target = new WebGLRenderTarget(1, 1, { samples: Math.min(4, gl.capabilities.maxSamples) })
    const composer = new EffectComposer(gl, target)
    const render = new RenderPass(scene, camera)
    const fxaa = new ShaderPass(FXAAShader)
    const output = new OutputPass()
    composer.addPass(render); composer.addPass(output); composer.addPass(fxaa)
    return { composer, fxaa, render, output }
  }, [gl, scene, camera])
  const fog = useMemo(() => new FogExp2('#164c60', 0), [])
  const background = useMemo(() => new Color(), [])
  useEffect(() => {
    const oldFog = scene.fog, oldBackground = scene.background
    scene.fog = fog
    scene.background = background
    return () => { scene.fog = oldFog; scene.background = oldBackground }
  }, [scene, fog, background])
  useEffect(() => () => { effects.composer.dispose(); effects.fxaa.dispose(); effects.output.dispose(); effects.render.dispose() }, [effects])
  useFrame(() => {
    // Use camera position, not a preset flag: orbiting across the water interface
    // and Follow Selected must get the same distance/depth attenuation.
    const depth = Math.max(0, -camera.position.y/verticalScale)
    const submerged = Math.min(1, depth/2)
    fog.density = scattering ? (1/Math.max(span*2.5, 1))*(1-submerged) + (.002+Math.min(depth,40)*.00008)*submerged : 0
    fog.color.set(scattering && depth > 0 ? '#164c60' : '#071522')
    background.copy(fog.color)
    if (!antialias) { gl.render(scene, camera); return }
    const dpr = gl.getPixelRatio(), key = `${size.width}:${size.height}:${dpr}`
    if (lastSize.current !== key) {
      effects.composer.setPixelRatio(dpr)
      effects.composer.setSize(size.width, size.height)
      effects.fxaa.uniforms.resolution!.value.set(1/(size.width*dpr), 1/(size.height*dpr))
      lastSize.current = key
    }
    effects.composer.render()
  }, 1)
  return null
}
