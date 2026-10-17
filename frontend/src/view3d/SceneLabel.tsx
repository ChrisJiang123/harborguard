import { useContext, useEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { CanvasTexture, LinearFilter, MathUtils, PerspectiveCamera, SRGBColorSpace, Vector3 } from 'three'
import type { Sprite } from 'three'
import { SceneLabelMode } from './SceneLabelContext'

interface SceneLabelProps {
  text: string
  color?: string
  borderColor?: string
  position?: [number, number, number]
  selected?: boolean
  pixelHeight?: number
  maxDistance?: number
  importance?: 'low' | 'normal' | 'high'
}

const worldPosition = new Vector3()

function roundedRect(context: CanvasRenderingContext2D, width: number, height: number, radius: number) {
  context.beginPath()
  context.roundRect(1, 1, width - 2, height - 2, radius)
}

/**
 * A WebGL-native label. Keeping labels inside the Three scene avoids creating a
 * second React DOM root for every target, which is both lighter and safe to
 * dispose when a layer or the whole 3D view is removed.
 */
export function SceneLabel({ text, color = '#bde8ff', borderColor = '#31526b', position = [0, 0, 0], selected = false, pixelHeight = 24, maxDistance = Infinity, importance = 'normal' }: SceneLabelProps) {
  const sprite = useRef<Sprite>(null)
  const size = useThree(state => state.size)
  const labelMode = useContext(SceneLabelMode)
  const texture = useMemo(() => {
    const scale = 2
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!
    context.font = `600 ${14 * scale}px Consolas, "Microsoft YaHei", sans-serif`
    const paddingX = 9 * scale
    const width = Math.ceil(context.measureText(text).width + paddingX * 2)
    const height = 25 * scale
    canvas.width = width
    canvas.height = height
    context.font = `600 ${14 * scale}px Consolas, "Microsoft YaHei", sans-serif`
    roundedRect(context, width, height, 7 * scale)
    context.fillStyle = '#061422e8'
    context.fill()
    context.lineWidth = (selected ? 2 : 1) * scale
    context.strokeStyle = selected ? '#eef8ff' : borderColor
    context.stroke()
    context.fillStyle = color
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(text, width / 2, height / 2 + scale * .25)
    const map = new CanvasTexture(canvas)
    map.colorSpace = SRGBColorSpace
    map.minFilter = LinearFilter
    map.generateMipmaps = false
    map.needsUpdate = true
    return { map, aspect: width / height }
  }, [text, color, borderColor, selected])

  useEffect(() => () => texture.map.dispose(), [texture])
  useFrame(({ camera }) => {
    if (!sprite.current) return
    sprite.current.getWorldPosition(worldPosition)
    const distance = camera.position.distanceTo(worldPosition)
    sprite.current.visible = labelMode === 'all' || selected || (labelMode === 'minimal' ? importance === 'high' : distance <= maxDistance)
    if (!sprite.current.visible) return
    const verticalFov = camera instanceof PerspectiveCamera ? MathUtils.degToRad(camera.fov) : Math.PI / 4
    const worldHeight = 2 * Math.tan(verticalFov / 2) * distance * pixelHeight / Math.max(size.height, 1)
    sprite.current.scale.set(worldHeight * texture.aspect, worldHeight, 1)
  })

  return <sprite ref={sprite} position={position} renderOrder={100} raycast={() => {}}>
    <spriteMaterial map={texture.map} transparent depthTest={false} depthWrite={false} sizeAttenuation />
  </sprite>
}
