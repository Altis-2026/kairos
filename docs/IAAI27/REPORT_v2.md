# Keeping a Language Model Honest About Radar: An Experience Report from Deploying Kairos

**Track:** IAAI-27, Track 3b — Deployment Insights: Experience Reports (2–4 pages)

> **Placeholder convention:** everything only the team can supply is marked
> `[[LIKE THIS]]`. Before submitting, grep the compiled PDF for `[[` and `[` —
> nothing should remain. See `GAP_ANALYSIS.md` §4 for how to source each one.

---

**Authors:** [[AUTHOR 1]], [[AUTHOR 2]], [[AUTHOR 3]], [[AUTHOR 4]]
**Affiliation:** [[TEAM / SCHOOL NAME]], [[CITY, STATE/COUNTRY]]
**Contact:** [[CORRESPONDING EMAIL]]

---

## Abstract

Kairos is a deployed web platform that lets people without remote-sensing
training query Sentinel-1 synthetic aperture radar (SAR) imagery in plain
language — floods, vessels, burn scars, oil slicks, forest loss, and sixteen
other analyses — and see results rendered on a 3D globe. A language model
translates the query; Google Earth Engine does all the computation server-side;
no raw scene is ever downloaded. We built it as a four-person student team over
roughly seven weeks and have operated it publicly since.

This report is about the part we did not anticipate. Putting a language model
in front of a scientific instrument turned out to be less an interface problem
than an *honesty* problem: the failure that matters is not a bad map, it is a
confident bad map. We describe the machinery we built against that — routing
every natural-language query through the same structured schema our
deterministic wizard produces, screening detections against measured
environmental confounders, and validating our production detectors against
independent published reference maps with the scores published openly. We then
give a candid account of what broke: an LLM gateway that silently routed us to
a retired model snapshot and took four attempts to diagnose, a health-status
redesign that made a genuine outage indistinguishable from a cold start, an
asynchronous job system we built and never needed, and eight consecutive failed
deployments that no code review could have caught. We close with the lessons we
would hand to another small team wiring a language layer onto a specialist
tool.

---

## 1. Introduction

Optical satellite imagery — the kind behind consumer mapping tools — cannot see
through cloud, smoke, or darkness. That is a serious limitation exactly when it
matters most: during the storm, during the wildfire, at night. Synthetic
aperture radar does not have this problem. The European Space Agency's
Sentinel-1 constellation images most of the globe every six to twelve days
regardless of weather or sunlight, and the data is free and public (Torres et
al. 2012). The catch is that using it requires knowing what a decibel of
backscatter difference means, how speckle and terrain corrupt it, and how to
drive a geospatial compute API — expertise that puts SAR out of reach for the
journalists, small NGOs, students, and individual responders who could most use
it.

Kairos lowers that barrier by putting a conversational layer in front of Google
Earth Engine (Gorelick et al. 2017). A user draws an area on a globe and picks
an analysis from a guided wizard, or types "flooding near Dhaka this week," and
gets an interpretable result without touching raw radar.

We expected the hard part to be the radar. It was not. Sentinel-1 change
detection is well-trodden, and Earth Engine exposes the preprocessing as
primitives. The hard part was that a language model will cheerfully resolve an
ambiguous query into a *specific*, *plausible*, *wrong* set of parameters, and a
SAR detector will cheerfully return a map of rain-wetted farmland labelled
"flood." Neither component fails loudly. Both fail persuasively. Everything
interesting we built is a response to that, and this report is organized around
it.

## 2. System Overview

Kairos has three layers.

A **FastAPI backend** exposes analysis, scene-preview, and query-parsing
endpoints. All SAR computation runs server-side inside Earth Engine: rather
than downloading Sentinel-1 scenes, which run to a gigabyte each and demand
their own calibration and terrain-correction pipeline, the backend sends a
computation graph to Earth Engine and receives a renderable map-tile URL and a
statistics dictionary. Nothing is downloaded, ever. This kept a four-person team
out of the raster-processing business entirely, at the cost of a hard dependency
on Earth Engine's quota and non-commercial terms — a trade we made deliberately
rather than by default.

Analyses are registered in a single dictionary that maps an ID to its function,
display name, category, palette, data sources, and expected runtime. Adding an
analysis type means writing one function and adding one entry; the frontend
sidebar rebuilds itself from a `/registry` endpoint that serializes the dict.
Twenty-two analyses are implemented at time of writing, including flood extent
via pre/post backscatter differencing in the tradition of automated Sentinel-1
flood chains (DeVries et al. 2020), vessel detection via CFAR-style adaptive
thresholding on VV, burn-scar mapping from the VH increase over bare rough soil,
subsidence, biomass, and a SAR-plus-optical flood consensus described in §3.

A **language layer** parses free-form queries into exactly the structured
parameters the wizard produces — analysis type, bounding box, date range —
using Claude Haiku 4.5 accessed through the OpenRouter gateway, with one
automatic reprompt on schema-validation failure. An agentic research assistant,
Janus, sits alongside it: a bounded tool loop with 21 callable tools that can
run real analyses, check data availability, search literature, and validate
against ground truth mid-conversation. Ordinary turns use Haiku; study-design,
adversarial-review, and autonomous "autopilot" turns escalate to Sonnet 4.6.
[[STATE PLAINLY WHETHER JANUS IS PUBLICLY REACHABLE TODAY OR GATED — see
GAP_ANALYSIS §8.3. Do not blur this.]]

The **frontend** is a Mapbox 3D globe with supporting panels for layer control,
before/after comparison, time-series extraction, and export to GeoTIFF, GeoJSON,
PDF, or a shareable link. It is served from Vercel; the backend runs on Cloud
Run; Firebase provides auth and persistence.

## 3. Keeping the Language Layer Honest

Four mechanisms, in increasing order of how much they cost us.

**One schema, two front doors.** Early on we debated making chat the only way
to run an analysis. We kept the wizard, and routed chat through the identical
schema, for a reason we did expect: testers wanted to see and correct the
literal parameters a query resolved to rather than trust an opaque translation.
[[INSERT REAL TESTER EVIDENCE HERE — this claim currently rests on assertion.
The strongest possible version is a verbatim quote from a tester who distrusted
a parse and switched to the wizard. See GAP_ANALYSIS §4.5.]]

The benefit we did *not* anticipate was operational: because a parsed query is
just wizard state, every language-layer failure is inspectable and correctable
in the same place we debug everything else. There is no separate pipeline to
instrument, and no class of bug that exists only in the chat path. If we built
another agentic layer over an existing tool tomorrow, this is the one decision
we would repeat without reconsidering.

**Refusing rather than guessing.** Our two-instrument flood consensus overlays
a Sentinel-1 backscatter drop with a Sentinel-2 NDWI water test, because radar
and optical fail differently — radar to wind roughening and shadow, optical to
cloud and turbidity — and classifies each pixel as radar-only, optical-only, or
agreed. It computes agreement *only* where cloud-free optical actually exists,
and if that is under 20% of the area it raises an error telling the user to run
the SAR-only detector instead. A consensus of one method is not a consensus.
Building the refusal path took longer than building the detection.

**Measuring confounders instead of naming them.** Every detector has known
false-positive modes: rain-wetted farmland mimics flood, calm wind mimics an oil
slick, harvest mimics clearing. Warning users about these in prose is cheap and
nearly worthless. Instead, for a given detection we pull the independent
environmental drivers for that exact area and window — CHIRPS daily rainfall,
ERA5-Land wind, ESA WorldCover land cover — and apply a transparent per-analysis
rule set that reports, for example, that 48 mm of rain fell in the five days
before the flood window, so wetted soil is a live alternative explanation. The
numbers are real; the interpretation is an explicit heuristic, and we label it
as a screening aid rather than a verdict.

**Publishing our own accuracy.** Three benchmarks re-run the *production*
detectors — not a special validation path — over historical events with
independent published reference maps: the 2017 Brahmaputra monsoon against the
Global Flood Database (Tellman et al. 2021), the 2018 Camp Fire against MODIS
MCD64A1, and 2020 Rondônia clearing against Hansen Global Forest Change. We
compute IoU, precision, recall, and F1 by pixel area, server-side, at request
time, and every run is logged to a public scoreboard endpoint. Results:

| Benchmark | IoU | Precision | Recall | F1 |
|---|---|---|---|---|
| Brahmaputra flood, 2017 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| Camp Fire, 2018 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |
| Rondônia clearing, 2020 | [[ ]] | [[ ]] | [[ ]] | [[ ]] |

[[RUN THESE — GAP_ANALYSIS §4.1 has the exact commands. Report whatever comes
back. A mediocre honest number with a stated method is worth more here than a
good number with no method, and this track will read it that way.]]

The caveats travel with every result and belong in the paper too: the references
are coarser than Sentinel-1 (250–500 m against 10 m), are built from different
sensors carrying their own error, and agreement is computed at the reference's
native scale. These are indicative figures, not survey-grade truth. Publishing
them openly is the point: if the numbers were bad, they would be bad in public.

## 4. What Went Wrong

**A model ID is not a stable resource.** Our natural-language layer began
returning 404s on every call. The queries were well-formed, our key was valid,
and the gateway reported no outage. The cause was three layers down: the model
we had pinned, Claude 3.5 Haiku, had been retired months earlier, and the only
provider on our gateway still advertising it was serving a deprecated
end-of-life snapshot that answered every request with a 404.

It took four attempts to land the fix, and the sequence is the lesson. We first
routed *around* the bad provider with a denylist. That appeared to work and did
not: the model identifier we used let requests slip past the ignore-list back to
the same dead backend. We then switched to a positive pin — an allowlist naming
the first-party provider only — which worked. Finally we accepted the actual
diagnosis, which was not a routing problem at all: the model was simply gone. We
moved to Claude Haiku 4.5 and deleted the provider pinning entirely, because a
current model needs none.

We take two things from this. First, the abstraction that makes a multi-provider
gateway convenient — you name a model, someone serves it — is the same
abstraction that hid a dead backend from us for hours. Second, denylisting
providers is a fragile reflex; pin positively, and treat provider-level 404s as a
distinct alarm from your own bugs, because they look nothing alike in a stack
trace and we spent our first hours looking in our own code.

**A status indicator that could no longer say "broken."** Users intermittently
saw the app report the API as offline when it was merely cold-starting: Cloud
Run scaled to zero, and the container blocked on Earth Engine's initialization —
a network round-trip to Google — before it could answer a health check.

Our first fix was to add a "waking up" state to the status badge. This was worse
than the bug. The new state never timed out, so a genuine outage was
indistinguishable from a cold start, and we had built a UI that could no longer
express "actually broken." We deleted the state. The real fix was
architectural and elsewhere: start Earth Engine initialization on a background
thread, let the app open its port and answer health checks immediately, and have
only the routes that actually touch Earth Engine wait on a readiness handshake.
Setting a minimum instance count removed the remaining cold starts.

The generalizable point is that we reached for a UI state to describe a
backend problem, and adding vocabulary to the symptom cost us the ability to
report the disease.

**An asynchronous job system we built and never needed.** Our first version ran
every analysis inside the request cycle, and large areas over wide date ranges
pushed past reasonable timeouts. We built a Redis-backed queue with a separate
worker process and a status-polling endpoint — and, along the way, a good bug:
the worker silently failed until we realized it must initialize Earth Engine
itself, because it does not share memory with the API server that queued the
job.

We should report honestly that none of this is what runs in production. The
deployed path is synchronous by design: Earth Engine calls block, so FastAPI
runs them in its threadpool, and the latency problem was actually solved by
moving initialization off the startup path and eliminating cold starts. The
queue remains in the codebase, optional, with a transparent synchronous
fallback. We built the sophisticated thing, and the fix turned out to be
somewhere else entirely — which is worth saying out loud, because the version of
this report where we describe our elegant job architecture would have been both
more flattering and untrue.

**Eight deployments that no code review could have caught.** Over two days our
deploy pipeline failed eight consecutive times: a missing Artifact Registry
repository, unset secrets, three Google Cloud APIs not enabled, two separate
missing IAM roles, a service-account key that had to be regenerated, and a
Firebase Hosting site that did not exist. Weeks later we found the backend had
been running as a service account with no Earth Engine access at all.

None of these were hard, and none of them were visible in the code being
reviewed. That is the actual finding: permissions, quotas, and API enablement
are invisible to your test suite and your reviewer, and they fail at deploy
time in an environment nobody is watching. We had estimated infrastructure setup
as a rounding error before "the real work." It was closer to a fifth of our
calendar time.

**Two smaller admissions.** We left our database in open test mode, with no
security rules, through most of development — the right default for early
velocity, but it auto-expires and is trivially easy to forget before opening a
tool to outsiders. And our first instinct for keeping a frozen version reachable
for an external evaluation was simply to keep the live URL updated, which meant
an ordinary development bug could reach an evaluator with no clean rollback. We
now tag a release, deploy that exact snapshot to a URL we commit not to touch,
and move daily work to a separate branch.

[[OPTIONAL, see GAP_ANALYSIS §3.4: the base64-in-YAML incident, and the broader
question of whether to state that Kairos was built substantially with an AI
coding agent. Our recommendation is to own it — the public commit history makes
it evident to any reviewer who clicks through, and it is squarely on-topic for
this track.]]

## 5. Deployment Status

Kairos is deployed and publicly reachable. It is not in sustained production
use, and we describe it as early deployment rather than overstate it.

As of [[DATE]], it has been used by [[N]] people across [[M]] sessions,
[[DESCRIBE WHAT WAS ACTUALLY EXERCISED]]. Feedback has centred on
[[SPECIFIC THEMES — verbatim confusion points are worth more than summary]].
Analyses typically complete in [[MEASURED MEDIAN]] for a city-scale area, with
[[RANGE]] across analysis types. On a hand-scored set of [[K]] natural-language
queries, the parser produced fully correct parameters [[X]] times; the failures
were concentrated in [[CHARACTERIZE THE FAILURE MODE]].

[[All of these are sourceable — GAP_ANALYSIS §4. If the honest usage number is
small, state the small number. This track treats early deployment as a category,
not a weakness, and a specific small number reads as credible where a vague
large one does not.]]

## 6. Lessons

**Give the language layer no private state.** Routing natural-language queries
through the same structured schema a deterministic UI already produces means the
model's failures surface as inspectable, correctable application state rather
than as a separate pipeline with its own debugging story. This was the cheapest
good decision we made.

**Warnings are not screening.** Telling a user that wet farmland can mimic flood
costs nothing and changes nothing. Pulling the actual rainfall for their actual
window and telling them what it implies is a different product. If your system's
outputs have known false-positive modes, the honest version measures them.

**Publish your accuracy before someone asks.** Running production detectors
against independent reference maps and putting the scores in public is
uncomfortable and it is the only thing that distinguishes a measured claim from
a marketing one. Build the harness early; it is much harder to add after you
have a number you like.

**Pin models positively and alarm on provider errors separately.** A model
identifier is a name for something that can be withdrawn. Denylists are the
wrong shape for this problem, and a gateway's 404 will spend your debugging time
in your own code unless you make it look different from your own failures.

**Budget real calendar time for multi-provider infrastructure.** The failure
mode is not difficulty, it is quantity and invisibility: every mismatched
project ID, unenabled API, and missing IAM role fails at deploy time, in a place
no reviewer is looking.

**Freeze external-facing deployments deliberately.** A tagged release on a URL
you commit not to touch is cheap insurance against ordinary development reaching
someone depending on stability — a judge, a pilot user, a reviewer.

## 7. Conclusion

Kairos's premise is that the barrier between public SAR data and the people who
could use it is mostly an interface problem. What we learned building it is that
the interface problem is really a trust problem: a language model in front of a
scientific instrument makes the tool reachable and simultaneously makes it
easier to be confidently wrong, and most of our engineering ended up on that
second half. Our next steps run the same direction — turning a flood polygon
into an estimate of affected population and buildings rather than square
kilometres, and widening the validation suite so more of what we ship is
measured rather than asserted. We offer this account because the process
failures — the withdrawn model, the status state that could not report an
outage, the job queue we did not need, the invisible permissions — seem likely
to recur for any small team wiring an agentic layer onto a specialist scientific
tool, whatever the domain.

---

## References

DeVries, B.; Huang, C.; Armston, J.; Huang, W.; Jones, J. W.; and Lang, M. W.
2020. Rapid and robust monitoring of flood events using Sentinel-1 and Landsat
data on the Google Earth Engine. *Remote Sensing of Environment*, 240: 111664.

Gorelick, N.; Hancher, M.; Dixon, M.; Ilyushchenko, S.; Thau, D.; and Moore, R.
2017. Google Earth Engine: Planetary-scale geospatial analysis for everyone.
*Remote Sensing of Environment*, 202: 18–27.

Tellman, B.; Sullivan, J. A.; Kuhn, C.; Kettner, A. J.; Doyle, C. S.;
Brakenridge, G. R.; Erickson, T. A.; and Slayback, D. A. 2021. Satellite
imaging reveals increased proportion of population exposed to floods. *Nature*,
596: 80–86.

Torres, R.; Snoeij, P.; Geudtner, D.; Bibby, D.; Davidson, M.; Attema, E.; et
al. 2012. GMES Sentinel-1 mission. *Remote Sensing of Environment*, 120: 9–24.

---

## Figure to produce

One architecture diagram (GAP_ANALYSIS §5). The load-bearing element is that
the wizard path and the natural-language path **converge on one schema** before
anything reaches Earth Engine — that convergence is the paper's argument, so the
figure should make it visually obvious rather than drawing a generic four-box
stack.
