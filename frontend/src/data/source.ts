import { useHarbor } from '../store/useHarbor'
import { startMock } from './mock'
import { startReplay } from './replay'
import { startLive } from './ws'

export function startSource(): () => void {
  useHarbor.getState().reset()
  const params = new URLSearchParams(window.location.search)
  if (params.get('mock') === '1') return startMock()
  const file = params.get('replay')
  if (file) return startReplay(file)
  if (params.get('live') === '1') return startLive()
  return startMock(true)
}
