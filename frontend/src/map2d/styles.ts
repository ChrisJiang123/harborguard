import { LEVEL_COLORS, ZONE_COLORS } from '../theme'
import type { Cls, Level, ZoneState } from '../types/contract'

export function zoneStyle(state: ZoneState, highlighted = false, focused = false) {
  return { color: highlighted ? '#EF4444' : focused ? '#7dd3fc' : ZONE_COLORS[state], fillColor: ZONE_COLORS[state], fillOpacity: state === 'open' ? 0 : 0.25, weight: highlighted ? 4 : focused ? 3 : 1.2, dashArray: highlighted ? '8 5' : focused ? '5 4' : undefined, opacity: highlighted || focused ? 1 : 0.8 }
}

const SYMBOLS: Record<Cls, string> = {
  unknown: '<text x="16" y="22" text-anchor="middle" fill="currentColor" font-size="24" font-weight="700">?</text>',
  uuv: '<rect x="7" y="11" width="19" height="10" rx="5" fill="currentColor"/><path d="m5 10 5 6-5 6M23 10l4-4" fill="none" stroke="currentColor" stroke-width="2"/>',
  fish_school: '<g fill="currentColor"><circle cx="11" cy="11" r="3"/><circle cx="22" cy="12" r="2.7"/><circle cx="15" cy="21" r="3"/><circle cx="24" cy="22" r="2"/><circle cx="7" cy="20" r="2"/></g>',
  debris: '<rect x="8" y="8" width="16" height="16" rx="2" fill="currentColor" transform="rotate(15 16 16)"/>',
  marine_mammal: '<ellipse cx="16" cy="16" rx="10" ry="5" fill="currentColor"/><path d="m25 16 5-5v10Z" fill="currentColor"/>',
  vessel: '<path d="M9 11h14l3 10-10 5L6 21Z" fill="currentColor"/><path d="M16 3v9m0-7 7 4h-7" stroke="currentColor" stroke-width="2" fill="none"/>',
}

export function targetIconHTML(cls: Cls, level: Level, selected: boolean) {
  const symbol = SYMBOLS[cls] ?? SYMBOLS.unknown
  return `<span class="target-symbol ${selected ? 'is-selected' : ''} ${level === 3 ? 'is-critical' : ''}" style="color:${LEVEL_COLORS[level]}"><svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">${symbol}</svg></span>`
}

export function buoyIconHTML(status: 'ok' | 'down' | 'pending') {
  return `<span class="buoy-map-symbol ${status}"><span class="buoy-ripple"></span><span class="buoy-core">${status === 'down' ? '×' : ''}</span></span>`
}
