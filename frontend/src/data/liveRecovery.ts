import { api } from './api'
import { useHarbor } from '../store/useHarbor'
import type { Detection, Option, StateMsg } from '../types/contract'

/** Recover bounded server history without inventing records that are absent from contract v1. */
export async function recoverLiveFromBackend(snapshot: StateMsg, signal?: AbortSignal): Promise<void> {
  const [eventsResult, logsResult] = await Promise.allSettled([
    api.events(0, signal),
    api.logs(200, signal),
  ])
  if (signal?.aborted) return
  const events = eventsResult.status === 'fulfilled' ? eventsResult.value : []
  const logs = logsResult.status === 'fulfilled' ? logsResult.value : []
  const options: Record<string, Option[]> = {}
  const detections: Record<string, Detection> = {}
  const optionIds = snapshot.alerts.filter(alert => alert.options_ready).map(alert => alert.id)
  const detectionIds = [...new Set(snapshot.tracks.map(track => track.detection_id).filter((id): id is string => !!id))]
  await Promise.all([
    ...optionIds.map(async alertId => {
      try { options[alertId] = (await api.options(alertId, signal)).options } catch { /* Event history may still contain it. */ }
    }),
    ...detectionIds.map(async detectionId => {
      try { detections[detectionId] = await api.detection(detectionId, signal) } catch { /* Bounded cache may have expired. */ }
    }),
  ])
  if (signal?.aborted) return
  useHarbor.getState().recoverLive(snapshot, events, logs, options, detections)
}
