import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  if (command === 'build' && process.env.VERCEL === '1') {
    const env = loadEnv(mode, process.cwd(), 'VITE_')
    for (const [key, protocol] of [['VITE_API_BASE', 'https:'], ['VITE_WS_URL', 'wss:']] as const) {
      let url: URL
      try { url = new URL(env[key] ?? '') }
      catch { throw new Error(`Set ${key} to the public Mac backend tunnel URL before building on Vercel.`) }
      if (url.protocol !== protocol || /^(localhost|127\..*|0\.0\.0\.0|\[::1\])$/i.test(url.hostname)
        || url.username || url.password || url.search || url.hash) {
        throw new Error(`${key} must use ${protocol}// with a public hostname and no credentials, query or fragment.`)
      }
    }
  }
  return { plugins: [react(), tailwindcss()] }
})
