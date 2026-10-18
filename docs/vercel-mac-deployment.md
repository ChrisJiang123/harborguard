# Vercel Frontend and Mac Backend Tunnel: Deployment Preparation

2026-10-17, America/Los_Angeles. This round prepared a deployment branch, production build, URL checks, and local browser smoke tests. It did not create a Vercel deployment or public tunnel and does not establish final integration or security acceptance.

## Versions and branch

Deployment branch: `codex/vercel-mac-tunnel-20261017`. Application commit: `e4d3f14e288acf5379edd86b6decc0d27db15d85`. Later delivery-document commits do not change application code. Obtain the final deployment SHA from the delivery message or `git rev-parse origin/codex/vercel-mac-tunnel-20261017`.

After fetching and checking remote ancestry, `e9ae07fbf1e233d83c983803b3992b165eae163c` was selected as the baseline: every other remote branch tip was already its ancestor at that check. This was verified rather than assumed from the branch name main. `origin/demo/mac-integration=a02eb04` had the same file tree as that main; `origin/fix/3d-shoreline-realism=94e9a4c` was also included.

A final fetch found newer main `d2d4c6fbdff72de5b2d2c02aab0c39723513f3a8` (#20, branch `codex/harborguard-submission-latest=51d69b3`), changing only README, the Chinese README, and two submission narratives. Directory comparisons confirmed `frontend/`, `backend/`, `agent/`, and `ml/` exactly matched the selected e9ae07f baseline. The deployment branch retained the just-tested functional version without additionally merging submission prose or merging into main.

| Component | Included commits |
| --- | --- |
| Latest shoreline/3D and English historical-record display | `00462e7`, `6d52b14`; integration tip `94e9a4c` |
| B option/metric update broadcasting | `fe0681e` (#16 merged) |
| B unresolved protection, anonymous observations, projection fixes | `6353421`, `97a8c75` |
| C4 configuration switching and test-data provenance correction | `6da0831`, `7c96ae1` |
| C actual-model self-check, English/template defaults, geometry helper | `e091506` |
| C frozen latency, three real-weight runs, actual fallback evidence | `9a14731` |
| Frontend deployment configuration from this round | `df6df167831ff589378dd4492f8b165a8332fa2c` |
| Backend CORS configuration from this round | `e4d3f14e288acf5379edd86b6decc0d27db15d85` |

The original project checkout remained at `6b18abb` with uncommitted work from other terminals. This round reused the independent managed worktree `/Users/chrisjiang/.codex/worktrees/c-acceptance-fixes/harborguard`, without switching, staging, or overwriting the original checkout. Existing processes on 5173/8000/8001 cannot be assumed to run this deployment commit merely from their ports or health=200.

## Vercel settings

| Setting | Value |
| --- | --- |
| Repository | `ChrisJiang123/harborguard` |
| Git branch | `codex/vercel-mac-tunnel-20261017` |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Node.js | `24.x` (locally tested `24.19.0`) |
| Install Command | `npm ci`; preserve the existing package-lock.json |
| Build Command | `npm run build` |
| Output Directory | `dist`, relative to frontend; repository path frontend/dist |

Create a Preview from the specified branch first. Verify branch and SHA during creation; importing a repository may default to main. For later Production use, configure that branch under Vercel Environments → Production → Branch Tracking, without merging main. See [official branch documentation](https://vercel.com/docs/git#production-branch).

Set these variables separately in the Preview/Production environment being used:

```dotenv
VITE_API_BASE=https://<mac-tunnel-hostname>/api
VITE_WS_URL=wss://<same-mac-tunnel-hostname>/ws
VITE_BATHYMETRY_URL=/data/seabed-dem.json
```

`VITE_*` values are public build-time configuration. API base requires `/api`; WebSocket requires `/ws`. Do not include keys, usernames, passwords, or tokens. Rebuild and redeploy after changing a tunnel address. Vercel builds validate HTTPS/WSS and reject missing values and loopback addresses. Ordinary local builds retain localhost defaults. This round confirmed the production bundle does not fall back to localhost:8000.

REST, metrics, Q&A, and sonar URLs come from `src/data/api.ts` using `VITE_API_BASE`. Map resource requests in `store/useMapData.ts` read the same variable; `data/ws.ts` uses `VITE_WS_URL`. Sonar URLs use the detection ID under the configured backend hostname, rather than incorrectly treating relative backend image_url as a Vercel static file. The existing request layer has `/api/agent/ask`, but the current page has no separate Q&A input; this round did not add one.

Following [official Vercel Vite SPA guidance](https://vercel.com/docs/frameworks/frontend/vite#using-vite-to-make-spas), `frontend/vercel.json` rewrites frontend page requests to `/index.html`. This handles page refresh only. API and WS connect directly to the tunnel; the SPA rewrite is not their proxy. An ordinary frontend build needs no Python and does not download/rebuild maps, train models, or run inference.

## Mac services and tunnel

The browser downloads static files from Vercel. REST and WebSocket share one HTTPS/WSS tunnel to Mac port 8000. Agent 8001 and Ollama 11434 remain local and need no additional public ports.

No usable `cloudflared` or Vercel CLI was installed on this Mac; Vercel can import through its website. This round did not install tools, start a tunnel, or alter shared services. Before switching 8000/8001, coordinate a maintenance window with the terminals using those ports, then start B/C from the selected deployment branch. Do not publish services still running from old checkout 6b18abb as though they were this version.

The commands below are for that coordinated window only. Use a clean checkout of the selected commit, the existing Python environment, and existing local credential file. Do not create environments, train models, or delete original databases.

```sh
# B terminal: use the actual Vercel page origin, without /api or a page path.
# Use a separate database for the first demo; retain old acceptance databases/logs.
ALLOWED_ORIGINS='https://<actual-frontend-hostname>,http://localhost:5173,http://127.0.0.1:5173' \
DEBUG_TRUTH_TRACKS=0 HARBORGUARD_DB=backend/runtime/vercel-demo-20261017.sqlite3 \
/Users/chrisjiang/Projects/harborguard/.venv/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8000 --workers 1

# C terminal: disable cloud for the no-cost connectivity smoke test.
# Local .env credentials never enter the frontend.
# --env-file reuses the existing file; explicit process variables take precedence.
CLOUD_PROVIDER=disabled BACKEND_BASE_URL=http://127.0.0.1:8000 \
BACKEND_WS_URL=ws://127.0.0.1:8000/ws AGENT_LANG=en \
OLLAMA_MODEL=harborguard-lora OLLAMA_FORMAT_OVERRIDES=harborguard-lora:json \
/Users/chrisjiang/Projects/harborguard/.venv/bin/python -m uvicorn agent.main:app \
  --env-file /Users/chrisjiang/Projects/harborguard/.env \
  --host 127.0.0.1 --port 8001 --workers 1

# Separate tunnel terminal, after cloudflared is installed.
cloudflared tunnel --url http://127.0.0.1:8000
```

The backend reads the CORS variable when creating the application. Editing .env alone does not change a running process. Without the variable, the original two local origins remain allowed; an explicit value replaces the complete list. Allow only actual frontend origins, not a wildcard for all vercel.app domains. This round did not change config.py/checkpoint fingerprints, physical parameters, approval rules, or P0 algorithms.

Quick Tunnel generates a different random hostname on each recreation; keep its terminal running during the demo. Use a named Tunnel if a fixed hostname is needed. Cloudflare documents [WebSocket support](https://developers.cloudflare.com/cloudflare-one/faq/cloudflare-tunnels-faq/#does-cloudflare-tunnel-support-websockets). [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) are for development/testing, with a 200 in-flight request limit and no availability guarantee; they are not completed production operations.

After obtaining the hostname, verify `/api/health`, then put its HTTPS/WSS URLs into Vercel configuration and deploy. Apply this branch's backend configuration with the actual frontend origin. New/replaced Preview URLs also require updating allowed origins. Check Agent `/health` for model, format, and language. The first no-cost smoke route is local LoRA → template. Restoring the existing OpenRouter route requires separate coordination of C's demo configuration.

## Verification and remaining items

- Production build passed with Node 24.19.0 / Vite 8.3.4. Eight negative cases covering missing values, HTTP/WS, loopback, URL credentials, and query parameters were rejected during build. The production bundle contained 0 localhost:8000 backend addresses. Existing locked dependencies were retained; no library upgrades.
- `npm run lint`, `check:deployment`, `check:a3`, and `check:recovery` passed. Q&A request-layer checks validated the public hostname, POST body, and existing 19-second budget without model requests. Full Python regression: **260 passed in 50.77s**, cloud disabled. Four new CORS cases covered defaults, specified Vercel origins, local origins, and rejection of unlisted origins.
- Local production preview on 5187 passed four checks: opening `/`, refreshing the home page, directly opening `/operations`, and refreshing it. All four WebSocket connections used the configured WSS URL. The page actually restored recommendations; metrics displayed harborguard-lora, test50/confirm60, 44/50 and 39/60, with fact-quality limits. Sonar images loaded. Page errors: 0; requests to local 8000/8001: 0; paid cloud calls: 0.
- The browser used controlled HTTPS/WSS contract test data, **not a real public tunnel or model acceptance test**. Actual Vercel routes, cross-device public HTTP/WS, deployed CORS, and post-deployment refresh remain **PENDING**. The 3D bundle still had a >500kB build warning; transport smoke tests do not establish 3D performance acceptance.
- B's specific repeated check that debris hazard zones never clear is recorded; this does not close every P0. The 0m near field remains unobserved/unsurveyed. Receiver misses, anonymous-geometry simulation assumptions, AIS truth coupling, and complex multi-target association limits remain. Scenario A L3 **505.0s ×3** exceeds the 400–500s target. No parameter or algorithm change hides that failure.
- C4: isolated English local/template=0/10; Chinese LoRA output cannot count as English success. Within ≤10s, test50/confirm60 achieved **44/50 and 21/60** respectively; factual passes were **44/50 and 39/60**. Both sets are synthetic. Historical failures and integer denominators remain unchanged.
- Existing A recovery, multi-operator, and race issues remain tracked under prior reports. Positive refresh smoke tests and existing script passes do not waive earlier failures. Actual Wi-Fi loss, projector readability, cross-device playback, and full venue acceptance still need owner confirmation.

See [build/browser evidence](evidence/vercel-mac-preparation-20261017.json), [production-page screenshot using controlled test data](evidence/vercel-mac-preparation-20261017.png), [C retest notes](C-acceptance-20261017-1743-retest-20261017-1911.md), and [B P0 audit](../backend/docs/survey-p0-audit.md). This round committed frontend, backend, and documentation separately and used ordinary Push to the deployment branch. It did not merge main or force-push.
