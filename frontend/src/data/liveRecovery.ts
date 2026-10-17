import { api } from './api'
import { useHarbor } from '../store/useHarbor'
import type { Detection, Option, StateMsg } from '../types/contract'

export interface LiveRecoveryContext {
  generation: number
  session: number
  previousSnapshotSeq?: number
}

let activeGeneration = 0

/** Start a new socket generation so responses from older connections become inert. */
export function beginLiveRecoveryGeneration(): number {
  activeGeneration += 1
  return activeGeneration
}

/** Invalidate a generation only if it still owns the active socket. */
export function invalidateLiveRecoveryGeneration(generation: number): void {
  if (activeGeneration === generation) activeGeneration += 1
}

/** Recover bounded server history without inventing records that are absent from contract v1. */
export async function recoverLiveFromBackend(snapshot: StateMsg, signal: AbortSignal | undefined, context: LiveRecoveryContext): Promise<void> {
  const isCurrent = () => !signal?.aborted && activeGeneration === context.generation && useHarbor.getState().session === context.session
  if (!isCurrent()) return
  const [eventsResult, logsResult] = await Promise.allSettled([
    api.events(0, signal),
    api.logs(200, signal),
  ])
  if (!isCurrent()) return
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
  if (!isCurrent()) return
  useHarbor.getState().recoverLive(snapshot, events, logs, options, detections, {
    eventsAvailable: eventsResult.status === 'fulfilled',
    eventsReturned: events.length,
    eventLimitReached: events.length >= 500,
    detailFailures,
    previousSnapshotSeq: context.previousSnapshotSeq,
  }, context.session)
}
