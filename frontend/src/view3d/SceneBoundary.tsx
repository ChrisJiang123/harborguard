import { Component } from 'react'
import type { ReactNode } from 'react'
import { useHarbor } from '../store/useHarbor'

export class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean; revision: number }> {
  state = { failed: false, revision: 0 }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <div className="three-fallback" role="alert"><h3>3D view temporarily unavailable</h3><p>Retry loading or continue with the 2D map.</p><div><button onClick={() => this.setState(state => ({ failed: false, revision: state.revision + 1 }))}>Retry 3D</button><button onClick={() => useHarbor.getState().setView('2d')}>Return to 2D</button></div></div>
    return <div key={this.state.revision} className="three-render-root">{this.props.children}</div>
  }
}
