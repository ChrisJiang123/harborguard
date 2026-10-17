import type { Cls } from './types/contract'

export const LEVEL_COLORS = ['#6B7280', '#3B82F6', '#F59E0B', '#EF4444'] as const
export const ZONE_COLORS = { open: '#6B7280', restricted: '#EF4444', clear: '#22C55E', unsurveyed: '#EAB308', blocked: '#EF4444' } as const
export const W = { C: 0.30, P: 0.25, B: 0.25, Z: 0.15, D: 0.05 } as const
export const FONT = { body: 14, metric: 24 } as const
// Scene metres match real metres by default. Enhanced vertical relief is opt-in.
export const VZ = 1
export const SEABED_DEPTH_M = 18
export const CLASS_NAMES: Record<Cls, string> = { unknown: '待识别目标', uuv: '水下无人航行器', fish_school: '鱼群', debris: '漂浮碎片', marine_mammal: '海洋哺乳动物', vessel: '船舶' }
export const clock = (t: number) => `${Math.floor(t / 60).toString().padStart(2, '0')}:${Math.floor(t % 60).toString().padStart(2, '0')}`
