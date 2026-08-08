# IAAI-27 Track 3b — Evidence Map

Every sentence in the call that a reviewer scores against, mapped to the exact
evidence Kairos can produce, and where it lands in the paper. Work top to
bottom; anything still marked ❌ when you submit is a scoring gap.

Track 3b's stated basis for evaluation: *"reviewed by the same committee under
the same single-blind process, with evaluation adjusted for length and
**weighted toward the usefulness and candor of the insight**."*

That sentence is the whole rubric. Usefulness and candor — not completeness,
not polish, not how much you built. Read every choice below against it.

---

## A. The four questions the call says a strong IAAI paper answers

### A1. "What new domain or problem was explored, and why was it interesting or hard?"

| Evidence | Status | Paper location |
|---|---|---|
| SAR is free, global, weather-independent, and effectively unusable without specialist training — a real access gap, not a manufactured one | ✅ have | §1 |
| The non-obvious framing: the hard part was **not** the radar. It was that both the LLM *and* the detector fail persuasively rather than loudly | ✅ have | §1 closing para |
| Domain novelty: NL interfaces to Earth-observation compute are thin on the ground; most SAR tooling assumes a remote-sensing user | ✅ have | §1 |

**Do not** claim SAR change detection is novel. It is not, you cite prior work
for it (DeVries et al.), and claiming novelty there would cost you credibility
you need elsewhere. The novelty is the *interface + assurance* layer.

### A2. "What new technical approach was applied, and what design decisions and alternatives shaped the solution?"

The call asks specifically for **alternatives considered**, not just decisions made.

| Decision | Alternative you actually rejected | Status |
|---|---|---|
| Server-side GEE compute | Download + process scenes locally (~1 GB/scene, own calibration/terrain-correction pipeline) | ✅ have |
| Chat *alongside* the wizard | Chat as the only entry point | ✅ have — but needs tester evidence, see C3 |
| One schema for both paths | Separate NL pipeline with its own params | ✅ have |
| Synchronous + threadpool + min-instances | Redis queue + worker + polling — **built, then abandoned** | ✅ have (§4) |
| Polling | WebSockets for progress | ✅ have |
| Positive provider pin, then none | Provider denylist — **tried, silently failed** | ✅ have (§4) |
| Registry-driven analysis types | Hardcoded per-analysis endpoints | ✅ have |

Abandoned approaches are explicitly rewarded ("accounts that report failures,
setbacks, and **abandoned approaches** alongside successes will be evaluated
more favorably"). You have three genuine ones. Name them as abandoned, not as
things you cleverly avoided.

### A3. "What impact did the application have, and how was it measured?" ⚠️ WEAKEST AREA

This is where you are thinnest and where Phase 1 data collection matters.

| Measurement | Instrument | Status |
|---|---|---|
| Detector accuracy vs independent ground truth | `gee/validation.py` + `/scoreboard` | ⚠️ 1 run each done — need N=5, see PHASE1 §1 |
| Per-analysis latency, and whether advertised estimates hold | `scripts/paper_data/collect_latency.ps1` | ❌ not run |
| NL parser correctness + characterized failure modes | `scripts/paper_data/collect_parses.ps1` | ❌ not run |
| Real usage volume | Cloud Run request metrics | ❌ not pulled |
| Model routing cost delta (Haiku vs Sonnet turns) | token counts | ❌ optional |

**Be careful how you word "impact."** You do not have impact in the sense of
"an NGO used this to direct relief." Claiming otherwise is the single fastest
way to lose a practitioner reviewer. What you have is a *deployed system with
measured behaviour and honest usage numbers* — say exactly that. The call's
Track 3b explicitly accommodates this; Track 1 would not.

### A4. "What happened on the way to deployment: what went wrong, what was redesigned, what was learned?" ✅ STRONGEST AREA

| Failure | Redesign | Transferable lesson | Status |
|---|---|---|---|
| Gateway served a retired model snapshot; 404 on every call | denylist → allowlist → migrate model → remove pinning | A model ID is not a stable resource; alarm on provider errors separately from your own | ✅ |
| Cold start + blocking GEE init read as "API offline" | background init + readiness handshake + min-instances | Adding a UI state to describe a backend problem cost the ability to report a real outage | ✅ |
| Async job system | built, never shipped; real fix was elsewhere | Build the simple thing until measurement says otherwise | ✅ |
| 8 consecutive deploy failures (IAM, APIs, secrets, registry) | — | Permissions are invisible to your test suite and fail where nobody is watching | ✅ |
| Firestore left in open test mode | real rules | Velocity defaults auto-expire and are easy to forget | ✅ |
| Live product vs judged snapshot | tagged release on a frozen URL | Cheap insurance for anyone depending on stability | ✅ |
| Benchmark disagreement found *by the harness we wrote* | see B2 | Your own evaluation harness turning up a problem is the best possible advertisement for having one | ⚠️ pending Phase 1 |

Seven distinct, dated, commit-traceable failures. This is genuinely strong and
is why this track is the right home for the paper.

---

## B. Track 3b topic areas — which you hit

The call lists seven areas. You need not hit all; you hit four well.

### B1. "Path to Responsible Deployment: evaluation harnesses… pre-deployment safety cases" ✅ STRONG
- `gee/validation.py` — production detectors, not a special path, against
  Global Flood DB / MCD64A1 / Hansen
- `scoreboard.py` — every run published, never cherry-picked
- `gee/confounders.py` — measured false-positive screening (CHIRPS/ERA5/WorldCover)
- `gee/consensus.py` — **refuses** below 20% cloud-free optical coverage
- Janus hard rules: no uncited references, no unrun numbers
- `provenance.py` — HMAC-signed results, `POST /verify`

### B2. "What Went Wrong and Why… failure modes specific to generative and agentic systems" ✅ STRONG
Everything in A4. The retired-snapshot incident is the headline, and it is
squarely a *generative-system deployment* failure rather than a generic bug.

⚠️ **Include the benchmark result honestly.** Your first fire run returned IoU
0.0 across four repeats. Whatever the cause turns out to be, the *story* — "we
built a validation harness, pointed it at ourselves, and it told us something we
did not want to hear" — is exactly this section's subject matter. A paper that
reports that is more credible than one reporting three tidy numbers.

### B3. "Deployment Economics and Efficiency: cost and latency engineering with measured production impact, from… model routing" ⚠️ PARTIAL
- Per-turn routing: Haiku 4.5 for tutoring, Sonnet 4.6 for design/review/autopilot
- Cold-start elimination, min-instances, background init — real latency engineering
- ❌ Missing: the *measured* part. Two sentences with real numbers converts this
  from a mention to a hit.

### B4. "Operating AI Systems in Production: monitoring, observability, guardrails… tracing and sandboxing of agentic systems" ⚠️ PARTIAL
- Janus: bounded tool loops (`MAX_TOOL_ROUNDS=6`, `AUTOPILOT_TOOL_ROUNDS=14`) —
  a real containment mechanism for an autonomous agent
- Tool events persisted per turn = an audit trail
- Health/status badge, keep-warm cron
- ⚠️ Depends entirely on the Janus availability answer (§D2)

### Not applicable — do not stretch to reach them
Data Quality Tools · Compliance/EU AI Act · Impact on Business Models.
Reaching for these would dilute a focused report. Four solid hits beats seven
thin ones under a "usefulness and candor" rubric.

---

## C. Submission requirements — hard gates

| Requirement | Status |
|---|---|
| 2–4 pages, AAAI two-column, **CameraReady** template (not anonymous) | ❌ still in Markdown |
| US Letter, high-res PDF, fonts embedded | ❌ |
| Single-blind: author names and affiliations **must** be present | ❌ needs §D1 |
| "Authors from the deploying organization are expected" | ✅ you are the deploying org — say so explicitly |
| Self-contained without supplementary material | ✅ current draft is |
| Originality — Congressional App Challenge is not a refereed venue | ✅ but read the form's exact wording yourself |
| Submitted via OpenReview to **IAAI-27**, Track 3b | ❌ |

### C3. The one unsupported claim in the current draft
§3 says testers wanted to see and correct the parameters a query resolved to.
**Right now that rests on assertion.** It is also the justification for your
central design decision, so a reviewer will notice. One verbatim tester quote
fixes it. If no tester ever actually said this, cut the claim and rewrite the
decision as an engineering judgement — do not leave an invented user finding in
a paper whose whole argument is about honesty.

---

## D. Decisions blocking the writeup

**D1. Authors, order, affiliation, contact email.** Blocks the template step
entirely. Ten minutes on a call.

**D2. Is Janus reachable by a real user today?**
- If yes → it is a deployed agentic system, and B4 becomes a strong hit.
- If gated/waitlisted → say "built, not yet released" and drop the B4 claim to
  a sentence.
- Blurring this is the highest-risk sentence in the paper. `docs/JANUS.md`
  describes paid tiers and a waitlist; a reviewer who reads the repo will check.

**D3. Do you state that Kairos was substantially AI-built?**
Recommendation: yes. ~30 commits on `claude/*` branches are public; a reviewer
who clicks through will see it. Volunteering it costs nothing and is on-topic
for a track about agentic systems. Being caught omitting it is expensive in a
paper arguing for candour. The base64-into-YAML incident (`bd4cbaa`) then
becomes usable as a genuine agentic-tooling failure.

**D4. What to do about the fire/deforestation benchmark numbers.** See B2 —
report them, whatever they say, with the diagnosis you actually reach.

---

## E. Order of operations

1. Push the `parse_only` change and let the deploy finish — the parser
   harness needs it live
2. `collect_benchmarks.ps1 -Runs 5` (~20 min, unattended)
3. `collect_latency.ps1 -Runs 3` (~10 min, unattended)
4. `collect_parses.ps1` (~3 min) then hand-score the CSV (~45 min, and this is
   the part that cannot be skipped or automated)
5. Diagnose the fire 0.0 — compare the tile URLs on a map
6. Pull Cloud Run request metrics over the full deployment window
7. Collect tester quotes (D-day dependency: real humans, start asking now)
8. Settle D1–D4
9. Fill every `[[ ]]` in `REPORT_v2.md`
10. Move into the AAAI CameraReady template, build the figure, check page count

Steps 2–4 run unattended. Step 7 depends on other people, so **send those
messages before you start step 2**, not after.

---

## F. What actually decides acceptance

Under a rubric weighted to "usefulness and candor," the ranking is:

1. **A4 / B2 — the failure stories.** Already your strongest asset. Seven
   dated, specific, commit-traceable failures with transferable lessons.
2. **A3 — measured behaviour.** Currently your weakest. Phase 1 fixes it. It
   does not need good numbers; it needs *real* numbers with a stated method.
3. **B1 — the assurance machinery.** Strong, and unusual for a report of this
   size. Most Experience Reports will not have a validation harness at all.
4. Everything else — formatting, the figure, page count. Mechanical. Necessary,
   but they do not win you anything.

The failure mode to avoid is spending the remaining time on 4 while 2 stays
unmeasured. A report with a mediocre honest accuracy table and a sharp failure
narrative beats a beautifully typeset one with vague claims — that is not
optimism, it is what the track's own evaluation sentence says.
