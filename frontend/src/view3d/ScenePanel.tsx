import { useState } from 'react'
import type { ReactNode } from 'react'

/** Native keyboard-accessible disclosure; closing it never unmounts controls. */
export function ScenePanel({ title, className, initiallyOpen = false, children }: { title: string; className: string; initiallyOpen?: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(initiallyOpen)
  return <details className={`three-panel ${className}`} open={open} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>{title}</summary>
    <div className="three-panel-body">{children}</div>
  </details>
}
