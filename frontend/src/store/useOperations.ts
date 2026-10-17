import { create } from 'zustand'

interface Toast { id: number; text: string; kind: 'error' | 'info' }
export const useOperations = create<{ pending: string | null; toast: Toast | null }>(() => ({ pending: null, toast: null }))
let nextToast = 0
export function notify(text: string, kind: Toast['kind'] = 'info') { useOperations.setState({ toast: { id: ++nextToast, text, kind } }) }

/** One outstanding operator mutation at a time; failed requests never become confirmations. */
export async function runOperation(label: string, operation: () => Promise<unknown>): Promise<boolean> {
  if (useOperations.getState().pending) return false
  useOperations.setState({ pending: label })
  try {
    await operation()
    return true
  } catch (error) {
    notify(`${label}失败：${error instanceof Error ? error.message : '请检查后端连接。'}`, 'error')
    return false
  } finally { useOperations.setState({ pending: null }) }
}
