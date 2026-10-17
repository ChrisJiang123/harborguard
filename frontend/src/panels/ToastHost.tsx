import { useEffect } from 'react'
import { useOperations } from '../store/useOperations'

export function ToastHost() {
  const toast = useOperations(s => s.toast)
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => { if (useOperations.getState().toast?.id === toast.id) useOperations.setState({ toast: null }) }, 8000)
    return () => clearTimeout(timer)
  }, [toast])
  if (!toast) return null
  return <div className={`toast ${toast.kind}`} role={toast.kind === 'error' ? 'alert' : 'status'}><span>{toast.text}</span><button aria-label="关闭操作提示" onClick={() => useOperations.setState({ toast: null })}>×</button></div>
}
