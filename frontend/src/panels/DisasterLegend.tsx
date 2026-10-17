import { useHarbor } from '../store/useHarbor'
import { ZONE_COLORS } from '../theme'

export function DisasterLegend({ className = 'map-legend' }: { className?: string }) {
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  if (!disaster) return null
  return <div className={className} aria-label="灾害图例"><span><i style={{ background: ZONE_COLORS.clear }} />可复航</span><span><i style={{ background: ZONE_COLORS.unsurveyed }} />待勘测</span><span><i style={{ background: ZONE_COLORS.blocked }} />封闭</span><span>▨ 离线覆盖 · 潜在盲区</span></div>
}
