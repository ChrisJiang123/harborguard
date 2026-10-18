import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Analytics } from '@vercel/analytics/react'
import './index.css'
import App from './App.tsx'
import { AppBoundary } from './layout/AppBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppBoundary><App /></AppBoundary>
    <Analytics />
  </StrictMode>,
)
