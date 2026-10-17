import { useEffect } from 'react'
import { startSource } from './data/source'
import { AppShell } from './layout/AppShell'

export default function App() {
  useEffect(() => startSource(), [])
  return <AppShell />
}
