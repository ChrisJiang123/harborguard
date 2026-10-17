import { Component } from 'react'
import type { ReactNode } from 'react'

export class AppBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (!this.state.failed) return this.props.children
    return <main className="app-fallback" role="alert"><h1>页面暂时无法显示数据</h1><p>请检查当前数据源格式，或先切换到本地演示。此提示不代表操作已成功，重新加载后请核对实际状态。</p><div><button onClick={() => location.reload()}>重新加载</button><a href="/?mock=1">打开本地演示</a></div></main>
  }
}
