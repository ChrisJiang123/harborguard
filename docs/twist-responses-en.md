# HarborGuard - Three Twist Responses

Prepared 17 October 2026. Lens: Ports & Logistics. This is submission-ready copy, not a receipt of submission to Devpost or the participant portal.

## Twist 1 - A federal funding pathway

**Our proposed primary federal R&D route is NSF SBIR Phase I, through America's Seed Fund.** The next research challenge is to move beyond a synthetic demonstration: can real acoustic observations and calibrated uncertainty support conservative port decisions across noisy and unfamiliar sites?

We would propose a feasibility study with three work packages:

1. Build an authorized, independently labeled real-echo evaluation set with a U.S. port or research partner. Separate training, calibration and held-out test sites.
2. Measure domain shift, missed hazards, false alarms and dangerous false-clear outcomes. Keep unresolved observations separate from survey coverage.
3. Evaluate calibrated confidence and bounded re-observation, then compare operator decisions with the current synthetic baseline in a supervised, non-operational pilot.

Success criteria would be agreed with the partner before data collection. We would report failure rates, uncertainty, throughput and operator workload rather than treat a green map or a simulated time estimate as a safety certificate. The requested work is an unproven research question; installing the current dashboard alone would not establish NSF program fit.

**Application route:** suitability assessment -> Project Pitch -> invitation -> full Phase I proposal in an eligible cycle. NSF funding is competitive; we have no invitation or award, and the current team has not been verified as an eligible applicant. The program requires an eligible U.S. small business, ownership/control qualifications, U.S.-based R&D and an eligible PI. We must check these before presenting an application plan as executable. Any international commercial rollout would be separate from the proposed U.S. R&D work and subject to the award's rules.

First actions after the hackathon: confirm applicant eligibility, seek an authorized U.S. pilot partner, document the technical novelty and commercial need, and prepare the Project Pitch. We do not assume the next published full-proposal deadline is reachable without an invitation.

Official references, checked 17 October 2026:

- [NSF SBIR/STTR program and NSF 26-510](https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology)
- [NSF eligibility requirements](https://seedfund.nsf.gov/solicitation-eligibility/)
- [Project suitability and Project Pitch](https://seedfund.nsf.gov/apply/project-pitch-information/)

## Twist 2 - From Los Angeles to Shanghai

**Our international adaptation example is Shanghai's Yangshan port. This is a proposed replication plan, not an existing partnership, integration or field deployment.** Shanghai's official account describes digital-twin-enabled operations at Yangshan; it does not endorse HarborGuard or demonstrate that we can integrate with its systems.

The reusable idea is the decision workflow: observe -> track -> assess -> explain -> human approval. The local operating data and model calibration must change. The current code still contains Los Angeles-specific data and configuration; international portability has not yet been implemented or tested.

| What stays conceptually reusable | What must be localized and validated |
| --- | --- |
| Explicit clear / blocked / unsurveyed states | Authorized port polygons, channels, berths, assets and survey boundaries |
| Separation of coverage from unresolved observations | Surveyed depths, coordinate reference system, vertical/tidal datum, units and NoData handling |
| Tracking, risk explanation and bounded re-observation | Receiver geometry, noise, sound propagation, local vessel patterns and detector calibration |
| Human approval before security restrictions | Named local authority, operating procedures, permissions and audit responsibilities |
| REST/WS event-driven dashboard and replay concept | Mandarin interface, local terminology, access control, authorized data storage and deployment environment |

**Proposed rollout:** first configure a Shanghai-specific test data pack without changing the frozen public interface; then run local synthetic and labeled historical cases; next conduct an authorized shadow-mode pilot; finally request a separate operational safety review. Shadow mode means decision support only, with no automatic port restrictions or reopening authority.

Acceptance would measure held-out detection and false-clear rates, track continuity, unresolved-state persistence, event/history consistency, operator comprehension and behavior under real transport loss. Local thresholds would require calibration and review rather than copying Los Angeles defaults. A Mandarin translation is necessary but is not sufficient for deployment.

We would seek an authorized local port operator and research partner, not claim access to operational systems. Data-sharing, sensor permissions, security and applicable cross-border restrictions would be reviewed before any pilot. No live Shanghai data or overseas validation is included in the current demo.

Context source: [Shanghai government: Yangshan Port Phase IV](https://english.shanghai.gov.cn/en-Latest-WhatsNew/20260814/f4427a05be154fc4957a5f62d67d6f2e.html).

## Twist 3 - Poster it

Final organizer format: an English **A3 portrait PDF (297 x 420 mm)**, a 300 dpi PNG companion and editable Python source. The earlier A2/A4 exports are alternatives, not the required final upload. The poster contains an actual prototype screenshot, the decision workflow, the federal funding route, the Shanghai adaptation plan, measured prototype evidence and a GitHub QR code. Upload the A3 PDF to Drive, verify viewer access and paste its real Drive link into Devpost; this task has not performed that upload or final submission.

Evidence shown is pinned to **main a841bf9a70d8bf8237b9e03763852a34bed10368**: 232 Python tests passed / 2 skipped; approximately 4.98 Hz state delivery; one actual A/B/C 2D browser flow in 4 minutes 46 seconds. It is not a claim of complete acceptance. The B fix later pushed as 390687a has now been merged through #16; later main d46e479 also contains A's #18 changes. Those updates are not silently counted as part of the earlier full-system test run.

Synthetic observations, simulated AIS, model error, outstanding frontend recovery issues, unavailable 3D in the test browser and missing field validation remain disclosed. Funding is proposed, and Shanghai deployment is conceptual.

## Submission status

The official public Devpost requirements say Twist responses and proof go through the participant portal within six hours of each announcement. Preparing these files does not establish that those deadlines were met. The team must check its portal history and submit or seek organizer guidance as applicable. No portal response, funding application or Devpost submission has been sent by this task.

Sources: [official competition requirements](https://innovatela.devpost.com/), [official dates](https://innovatela.devpost.com/details/dates). The public deadline is 18 October at 01:00 EDT, equivalent to 17 October at 22:00 Los Angeles time. The pasted poster announcement's separate 1 PM wording is not treated as a verified extension or a verified date; confirm that upload detail with the organizer/portal.
