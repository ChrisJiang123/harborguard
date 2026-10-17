import { createContext } from 'react'

export type LabelMode = 'auto' | 'all' | 'minimal'
export const SceneLabelMode = createContext<LabelMode>('auto')
