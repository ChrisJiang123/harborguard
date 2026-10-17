import { create } from 'zustand'

interface ReplayDriver { play: (value: boolean) => void; seek: (value: number) => void; setSpeed: (value: number) => void }
export const useReplay = create(() => ({ loading: false, filename: '', position: 0, duration: 0, playing: false, speed: 1, driver: null as ReplayDriver | null, error: null as string | null }))
