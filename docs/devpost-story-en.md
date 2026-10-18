# HarborGuard

**Lens:** Ports & Logistics

**Tagline:** See underwater risk. Keep people in control.

## Inspiration

A port disruption is not just a detection problem. Operators must decide what to inspect, which response to consider and what remains uncertain. After a storm or suspicious underwater activity, scattered observations can produce both overreaction and unsafe confidence. We built HarborGuard to make that decision process visible.

## What it does

HarborGuard is a port-security and disaster-recovery digital-twin prototype with two connected workflows.

**Security:** synthetic acoustic observations and simulated AIS feed localization and tracking. Risk is explained through a three-level alert system. Active-sonar images are rendered and analyzed by the delivered YOLO model. The backend generates response options, and an Agent explains the current evidence. A recommendation does not impose restrictions: an operator must approve a valid option first.

**Recovery:** the system surveys zones, records confirmed obstacles and keeps unresolved observations separate from coverage. A missed detection, wrong class, uncertain result or unreliable near-field image does not become clear just because coverage reaches 100%. Candidate routes use confirmed-clear channels only.

The dashboard exposes live state, detection images, recommendations, decisions and a clearly labeled read-only replay.

## How we built it

The prototype combines Python, FastAPI, Pydantic v2, SQLite, REST and WebSocket; synthetic acoustic geometry and Kalman tracking; risk scoring and candidate-response comparison; and a React/TypeScript 2D/3D frontend. C's delivered sonar renderer and YOLO26n weights run on synthetic images. The Agent supports multiple routes, while this Windows acceptance run deliberately used the deterministic template fallback.

SQLite persists recommendations, decisions and simulation checkpoints. Event recovery remains bounded by the frozen 500-event API window. An automated build passing does not prove every recovery boundary is correct.

## What we actually demonstrated

At main **a841bf9a70d8bf8237b9e03763852a34bed10368**, the current acceptance run produced:

- 232 Python tests passed and 2 skipped; frontend build, lint and A1-A6 checks passed.
- Approximately 4.98 Hz live state delivery in an isolated real backend/Agent integration.
- Three repeatable full runs each of the synthetic Security and Recovery scenarios using the delivered real YOLO weights.
- One actual A/B/C browser flow in 4 minutes 46 seconds using 2D fallback: live Security -> level-three alert -> YOLO image -> template recommendation -> human approval -> Recovery -> replay.

The observed Recovery result was 6 clear, 3 blocked and 3 unsurveyed zones. The fuel berth remained unsurveyed at full coverage. Those counts are one simulation result, not a target hardcoded into the algorithm. Any time-saved display is a scenario assumption, not a measured operational saving or permission to reopen a port.

## Challenges and honest limits

The most important lesson was that coverage and certainty are different. We preserved original model-failure cases and added conservative unresolved-state handling rather than hide wrong classifications with more favorable data.

Current observations and AIS are synthetic or simulated. Real-ocean performance and operational safety are not certified. Some frontend recovery races remain; 3D was unavailable in the earlier Windows acceptance browser. A has supplied separately recorded 3D browser evidence, now used in the poster with its replay label preserved. The B patch for metric-only response-option broadcasts was separately tested (237 passed, 2 skipped) and merged in PR #16. Official main checked out during this update is e9ae07f, including A's #18 and C's #19 language/configuration updates. Older full-system test totals are not automatically acceptance of the newer combination. C's new English mode can fall back to English templates when model output remains Chinese; it does not prove English LoRA quality. Separate model evaluations retain their own provenance.

## Dual-use fit

Everyday use is operator training, investigation and response comparison. Disruption use is conservative survey prioritization and candidate-route planning. The same explainable, human-controlled workflow serves both without granting the software authority to close or reopen real facilities.

## Twist 1 - Federal funding

Our proposed route is **NSF SBIR Phase I** for unproven R&D on real-echo validation and calibrated uncertainty across sites. We would first check applicant eligibility, build an authorized U.S. research partnership and submit a Project Pitch. Invitation, eligibility and award are not established. This is a future funding plan, not secured government support.

## Twist 2 - Global application

Our adaptation example is **Shanghai/Yangshan**, as a proposal rather than a deployment. Keep the decision workflow; localize authorized maps, depth/tide references, acoustic calibration, language, data controls and approval procedures. Validate with local labeled cases and shadow-mode trials before any operational use. The existing code is not yet validated as a portable multi-port product.

## Twist 3 - Poster

Our A3 portrait poster uses A's actual recorded **3D overview**, together with the workflow, proposed funding route, Shanghai adaptation plan, separately dated system measurements and a GitHub QR code. The screenshot remains labeled REPLAY; it is not presented as a new LIVE capture or as proof of current all-service acceptance. The poster is a print-ready PDF, with a 300 dpi PNG companion. The organizer requires a Drive link in Devpost: uploading the PDF, checking viewer access and pasting that real link are separate steps, not yet performed by this task.

## Responsible use

HarborGuard could be misused for unauthorized surveillance or unsafe operational decisions based on incomplete data.
Human approval and explicit uncertainty limit these risks; the synthetic prototype is not certified for navigation or port reopening.

## Built with / tools and sources

Python, FastAPI, Pydantic, SQLite, NumPy, Shapely, Pillow/OpenCV, PyTorch/Ultralytics YOLO26n; React, TypeScript, Vite, Leaflet, Three.js, React Three Fiber and Zustand; Codex and ChatGPT for development assistance. OpenStreetMap attribution remains on the actual dashboard screenshot. Sonar imagery and AIS in this demo are synthetic/simulated; public bathymetric layers retain their source labels and are not used to claim real sonar validation. The poster uses ReportLab, pypdf and Poppler. No claim is made that IBM Bob was used.

Before final submission, the team must confirm this list against its own contributions and disclose any additional APIs, third-party assets or AI tools actually used. Add every actual teammate, the pitch deck and the final playable video URL in Devpost. This file does not submit the project.

## Links and evidence

- [GitHub repository](https://github.com/ChrisJiang123/harborguard)
- [Acceptance report, pinned report commit](https://github.com/ChrisJiang123/harborguard/blob/a4d40277847519f614d54a7d2eae519cae1b1ff6/docs/final-delivery-20261017.md)
- [Merged B metric-broadcast fix](https://github.com/ChrisJiang123/harborguard/pull/16)
- [A's recorded 3D evidence](https://github.com/ChrisJiang123/harborguard/blob/e9ae07fbf1e233d83c983803b3992b165eae163c/docs/3d-shoreline-realism/README.md)
- [NSF program](https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology), [eligibility](https://seedfund.nsf.gov/solicitation-eligibility/), [Project Pitch](https://seedfund.nsf.gov/apply/project-pitch-information/)
- [Shanghai context](https://english.shanghai.gov.cn/en-Latest-WhatsNew/20260814/f4427a05be154fc4957a5f62d67d6f2e.html)

Video and pitch-deck files are not created or uploaded by this poster task. Do not publish a fabricated video URL, claim a pilot partner, or mark a portal response as submitted without its receipt.
