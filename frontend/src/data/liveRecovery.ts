import { api } from './api'
import { useHarbor } from '../store/useHarbor'
import type { Detection, Option, StateMsg } from '../types/contract'

/** Recover bounded server history without inventing records that are absent from contract v1. */
export async function recoverLiveFromBackend(snapshot: StateMsg, signal?: AbortSignal, previousSnapshotSeq?: number): Promise<void> {
  const [eventsResult, logsResult] = await Promise.allSettled([
    api.events(0, signal),
    api.logs(200, signal),
  ])
  if (signal?.aborted) return
  const events = eventsResult.status === 'fulfilled' ? eventsResult.value : []
  const logs = logsResult.status === 'fulfilled' ? logsResult.value : []
  const options: Record<string, Option[]> = {}
  const detections: Record<string, Detection> = {}
  let detailFailures = 0
  const optionIds = snapshot.alerts.filter(alert => alert.options_ready).map(alert => alert.id)
  const detectionIds = [...new Set(snapshot.tracks.map(track => track.detection_id).filter((id): id is string => !!id))]
  await Promise.all([
    ...optionIds.map(async alertId => {
      try { options[alertId] = (await api.options(alertId, signal)).options } catch { detailFailures++ }
    }),
    ...detectionIds.map(async detectionId => {
      try { detections[detectionId] = await api.detection(detectionId, signal) } catch { detailFailures++ }
    }),
  ])
  if (signal?.aborted) return
  useHarbor.getState().recoverLive(snapshot, events, logs, options, detections, {
    eventsAvailable: eventsResult.status === 'fulfilled',
    eventsReturned: events.length,
    eventLimitReached: events.length >= 500,
    detailFailures,
    previousSnapshotSeq,
  })
}
