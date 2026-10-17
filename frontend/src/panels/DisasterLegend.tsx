import { useHarbor } from '../store/useHarbor'
import { ZONE_COLORS } from '../theme'

export function DisasterLegend({ className = 'map-legend' }: { className?: string }) {
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  if (!disaster) return null
  return <div className={className} aria-label="Disaster legend"><span><i style={{ background: ZONE_COLORS.clear }} />Ready to reopen</span><span><i style={{ background: ZONE_COLORS.unsurveyed }} />Unsurveyed</span><span><i style={{ background: ZONE_COLORS.blocked }} />Blocked</span><span>▨ Offline coverage · Potential blind spot</span></div>
}
