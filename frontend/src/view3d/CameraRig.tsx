import { useEffect, useRef } from 'react'
import { OrbitControls } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { Vector3 } from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { cameraPreset, createTrackMotion, FLIGHT_SECONDS, sampleTrackMotion, smoothFlight } from './coordinates'
import type { CameraMode, SceneBounds } from './coordinates'

export function CameraRig({ mode, revision, bounds, verticalScale }: { mode: CameraMode; revision: number; bounds: SceneBounds; verticalScale: number }) {
  const selected = useHarbor(s => s.selectedTrackId)
  const controls = useRef<OrbitControlsImpl>(null)
  const camera = useThree(s => s.camera)
  const clock = useThree(s => s.clock)
  const flight = useRef({ active: false, at: 0, startCamera: new Vector3(), startTarget: new Vector3(), goalCamera: new Vector3(), goalTarget: new Vector3(), offset: new Vector3(), movement: new Vector3() })
  const motion = useRef(createTrackMotion())
  useEffect(() => {
    if (!controls.current) return
    const track = selected ? useHarbor.getState().tracks[selected] : undefined
    const asset = useMapData.getState().resources?.assets[0]
    const preset = cameraPreset(mode, bounds, track, asset, verticalScale)
    const plan = flight.current
    plan.startCamera.copy(camera.position)
    plan.startTarget.copy(controls.current.target)
    plan.goalCamera.fromArray(preset.position)
    plan.goalTarget.fromArray(preset.target)
    plan.offset.copy(plan.goalCamera).sub(plan.goalTarget)
    plan.at = clock.elapsedTime
    plan.active = true
    motion.current = createTrackMotion(track, verticalScale)
  }, [selected, mode, revision, bounds, camera, clock, verticalScale])
  useFrame((_, delta) => {
    if (!controls.current) return
    const track = selected ? useHarbor.getState().tracks[selected] : undefined
    const plan = flight.current
    if (mode === 'follow' && track) {
      plan.goalTarget.fromArray(sampleTrackMotion(motion.current, track, clock.elapsedTime, verticalScale))
      plan.goalCamera.copy(plan.goalTarget).add(plan.offset)
    }
    if (plan.active) {
      const progress = (clock.elapsedTime - plan.at) / FLIGHT_SECONDS
      const eased = smoothFlight(progress)
      camera.position.lerpVectors(plan.startCamera, plan.goalCamera, eased)
      controls.current.target.lerpVectors(plan.startTarget, plan.goalTarget, eased)
      if (progress >= 1) plan.active = false
      controls.current.update()
    } else if (mode === 'follow' && track) {
      plan.movement.copy(plan.goalTarget).sub(controls.current.target).multiplyScalar(1 - Math.exp(-8 * Math.min(delta, .1)))
      controls.current.target.add(plan.movement)
      camera.position.add(plan.movement)
      controls.current.update()
    }
  })
  return <OrbitControls ref={controls} makeDefault target={bounds.center} enableDamping dampingFactor={.09} minDistance={35} maxDistance={bounds.span * 4} maxPolarAngle={Math.PI * .92} rotateSpeed={.65} zoomSpeed={.85} onStart={() => { flight.current.active = false }} />
}
