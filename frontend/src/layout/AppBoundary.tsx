import { Component } from 'react'
import type { ReactNode } from 'react'

export class AppBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return <main className="app-fallback" role="alert"><h1>Unable to display data</h1><p>Check the current data format or open the local demo. No action has been confirmed; check the actual state after reloading.</p><div><button onClick={() => location.reload()}>Reload</button><a href="/?mock=1">Open local demo</a></div></main>
  }
}
