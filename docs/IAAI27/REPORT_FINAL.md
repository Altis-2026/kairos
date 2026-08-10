# Keeping a Language Model Honest About Radar: An Experience Report from Deploying Kairos

**Track:** IAAI-27, Track 3b, Deployment Insights: Experience Reports (2 to 4 pages)

**Author:** Amogh Vinaykumar
**Affiliation:** `[[TEAM / SCHOOL NAME]], [[CITY, STATE/COUNTRY]]`
**Contact:** amogh.vinaykumar@gmail.com

> One placeholder remains: the affiliation line. Everything else is filled with
> measured values. Search this file for `[[` before compiling.

---

## Abstract

Kairos is a deployed web platform that lets people without remote-sensing
training query Sentinel-1 synthetic aperture radar (SAR) imagery in plain
language, across twenty-two analysis types, and see results rendered on a 3D
globe. A language model translates the query, Google Earth Engine performs all
computation server-side, and no raw scene is ever downloaded.

This report is about the part we did not anticipate. Putting a language model in
front of a scientific instrument turned out to be less an interface problem than
an honesty problem: the failure that matters is not a bad map, it is a confident
bad map. We describe the machinery we built against that, then give a candid
account of what it caught. Our evaluation harness found sixteen of our
twenty-two analysis capabilities unreachable through the conversational
interface, because a system prompt had drifted from the registry it described;
fixing it moved parser accuracy from 85% to 92.5% on a 40-query test set. The
same harness scored one of our detectors at zero agreement with an independent
reference map, and the diagnosis was worse than a bug: it was confidently
measuring the wrong phenomenon. We also report an LLM gateway that silently
served a retired model snapshot, a health indicator we redesigned into being
unable to report a real outage, and an asynchronous job system we built and never
needed.

---

## 1. Introduction

Optical satellite imagery, the kind behind consumer mapping tools, cannot see
through cloud, smoke, or darkness. That is a serious limitation exactly when it
matters most: during the storm, during the wildfire, at night. Synthetic aperture
radar does not have this problem. The European Space Agency's Sentinel-1
constellation images most of the globe every six to twelve days regardless of
weather or sunlight, and the data is free and public (Torres et al. 2012). The
catch is that using it requires knowing what a decibel of backscatter difference
means, how speckle and terrain corrupt it, and how to drive a geospatial compute
API. That expertise puts SAR out of reach for the journalists, small NGOs,
students, and responders who could most use it.

Kairos lowers that barrier by putting a conversational layer in front of Google
Earth Engine (Gorelick et al. 2017). A user draws an area on a globe and picks an
analysis from a guided wizard, or types "flooding near Dhaka this week," and gets
an interpretable result without touching raw radar.

We expected the hard part to be the radar. It was not. Sentinel-1 change
detection is well-trodden, and Earth Engine exposes the preprocessing as
primitives. The hard part was that a language model will cheerfully resolve an
ambiguous query into a specific, plausible, wrong set of parameters, and a SAR
detector will cheerfully return a map of rain-wetted farmland labelled "flood."
Neither fails loudly. Both fail persuasively, and both did. Everything
interesting we built is a response to that.

## 2. System Overview

Kairos has three layers.

A **FastAPI backend** exposes analysis, scene-preview, and query-parsing
endpoints. All SAR computation runs server-side inside Earth Engine: rather than
downloading Sentinel-1 scenes, which run to a gigabyte each and demand their own
calibration and terrain-correction pipeline, the backend sends a computation
graph to Earth Engine and receives a renderable map-tile URL and a statistics
dictionary. Nothing is downloaded, ever. This kept a small team out of the
raster-processing business entirely, at the cost of a hard dependency on Earth
Engine's quota and non-commercial terms, a trade we made deliberately.

Analyses are registered in a single dictionary mapping an ID to its function,
display name, palette, and expected runtime. Adding an analysis means writing one
function and adding one entry; the frontend sidebar rebuilds itself from a
`/registry` endpoint that serializes the dict. Twenty-two analyses are
implemented, including flood extent via pre/post backscatter differencing in the
tradition of automated Sentinel-1 flood chains (DeVries et al. 2020), vessel
detection via CFAR-style adaptive thresholding on VV, burn-scar mapping from the
VH increase over bare rough soil, and a SAR-plus-optical flood consensus
described in Section 3. That registry-versus-description gap is the subject of
Section 4.1.

A **language layer** parses free-form queries into exactly the structured
parameters the wizard produces, analysis type, bounding box, and date range,
using Claude Haiku 4.5 through the OpenRouter gateway, with one automatic
reprompt on schema-validation failure. Median parse latency is 1.94 s. An agentic
research assistant, Janus, sits alongside it: a bounded tool loop with 21
callable tools that can run analyses, search literature, and validate against
ground truth mid-conversation, with study-design and adversarial-review turns
escalating from Haiku to Sonnet 4.6. Janus is in closed research preview,
unlocked per user by an individually issued access code, because every mentor
turn costs real model spend.

The **frontend** is a Mapbox 3D globe, served from Vercel, with the backend on
Cloud Run and Firebase for auth.

## 3. Keeping the Language Layer Honest

Four mechanisms, in increasing order of what they cost us.

**One schema, two front doors.** Early on we debated making chat the only way to
run an analysis. We kept the wizard and routed chat through the identical schema.
The benefit we anticipated was that users could see and correct the literal
parameters a query resolved to rather than trust an opaque translation. The
benefit we did not anticipate mattered more: because a parsed query is just
wizard state, every language-layer failure is inspectable in the same place we
debug everything else, and no class of bug exists only in the chat path. Section
4.1 is a direct consequence: the wizard was quietly correct about our own
capabilities the entire time the chat layer was wrong, which is how we found the
discrepancy at all.

**Refusing rather than guessing.** Our two-instrument flood consensus overlays a
Sentinel-1 backscatter drop with a Sentinel-2 NDWI water test, because radar and
optical fail differently, and classifies each pixel as radar-only, optical-only,
or agreed. It computes agreement only where cloud-free optical exists, and if
that is under 20% of the area it refuses, telling the user to run the SAR-only
detector instead. A consensus of one method is not a consensus. Building the
refusal took longer than building the detection.

**Measuring confounders instead of naming them.** Every detector has known
false-positive modes: rain-wetted farmland mimics flood, calm wind mimics an oil
slick, harvest mimics clearing. Warning about these in prose is cheap and nearly
worthless. Instead we pull the independent environmental drivers for the exact
area and window, CHIRPS rainfall, ERA5-Land wind, and ESA WorldCover land cover,
and report, for example, that 48 mm of rain fell in the five days before the
flood window, so wetted soil is a live alternative explanation. The numbers are
real; the interpretation is a labelled heuristic, a screening aid not a verdict.
Section 4.2 is what happens when this warning is not heeded.

**Publishing our own accuracy.** Four benchmarks re-run the production detectors,
not a special validation path, over historical events with independent published
references. Three compare pixel areas: the 2017 Brahmaputra monsoon against the
Global Flood Database (Tellman et al. 2021), the 2018 Camp Fire against MODIS
MCD64A1, and 2020 Rondônia clearing against Hansen Global Forest Change. Every
run is logged to a public scoreboard endpoint.

| Benchmark | IoU | Precision | Recall | F1 |
|---|---|---|---|---|
| Brahmaputra flood, 2017 | 0.214 | 0.544 | 0.260 | 0.352 |
| Camp Fire, 2018 | 0.000 | 0.000 | 0.000 | n/a |
| Rondônia clearing, 2020 | 0.017 | 0.022 | 0.080 | 0.035 |

These are weak numbers and we report them as they came back. The caveats travel
with every result and belong here too: the references are coarser than
Sentinel-1, 250 m to 500 m against 10 m, are built from different sensors
carrying their own error, and agreement is computed at the reference's native
scale. Section 4.2 is what happened when we investigated the zero.

A fourth benchmark, built but not yet run at submission time, scores ship
detection against AIS transponder broadcasts. It is deliberately not an IoU: a
point detector has no area to intersect, so it matches each radar return to the
nearest broadcast in time and reports precision as an explicit lower bound, since
an unmatched return may be a small craft under no AIS obligation rather than a
false detection.

## 4. What Went Wrong

### 4.1 Sixteen of twenty-two capabilities were invisible to the chat interface

We built a 40-query test set to score the natural-language parser, spanning
plain queries, colloquial phrasing, relative dates, ambiguous toponyms,
out-of-scope requests, multi-intent queries, and prompt injection. It
immediately found the parser silently refusing valid requests. Asked about "land
subsidence in Jakarta" and "urban growth in Shenzhen," it replied that Kairos
does not offer those analyses, in fluent, well-reasoned prose. Both are live
registry entries with working detectors.

The cause was upstream of the model. The system prompt teaching the parser what
Kairos can do had been written for the original six analysis types and never
updated as the registry grew to twenty-two. It stated explicitly that "only the
six ids in the table exist." The model was not hallucinating. It was correctly
following an instruction that had quietly become false, and it defended that
false position articulately, which is precisely why no one caught it by using
the product.

Correcting the prompt to match the registry moved accuracy from 85% (34/40) to
92.5% (37/40), with the improvement concentrated exactly where the diagnosis
predicted: the three previously refused queries, and nothing else changed.

What survived the fix is worth reporting too. The parser asked for clarification
rather than guessing on ambiguous toponyms ("flooding in Springfield"), declined
out-of-scope requests including weather forecasting and earthquake prediction,
refused to invent a bounding box for a fictional place, and did not comply with a
prompt-injection attempt to emit a fabricated flood area. Nineteen of forty
queries ended in a clarifying question, which we count as correct where the query
was genuinely underdetermined.

The transferable lesson: **a capability that exists in your system but not in
the text describing your system to your own language model does not exist from a
user's perspective.** Nothing about this failure looks like a bug. It looks like
a polite, well-reasoned answer. The deterministic wizard never had it, because it
reads the registry directly rather than a hand-maintained description of it, and
that asymmetry is the argument for keeping both paths on one schema.

### 4.2 Our own harness caught a detector measuring the wrong thing

The Camp Fire benchmark returned zero overlap with the reference map, identical
across four repeated runs, which ruled out noise. Investigating it produced a
worse finding than a coordinate bug.

Running the production detector over the fire area and inspecting the output
directly, the detected pixels sat in the flat agricultural land near Chico,
while Paradise and Magalia, where the fire did its catastrophic damage, showed
almost nothing. Kairos's own optical cross-check corroborated this
independently, reporting 8.7% agreement between the SAR detection and a
Sentinel-2 confirmation pass over the same area and window. The system also
reported a wide uncertainty band, 9.82 to 44.18 km² across its threshold
ensemble, against a headline estimate of 20.6 km².

The likeliest explanation is the confounder our own screening module documents
for this analysis type: agricultural harvest and ploughing raise VH backscatter
much as a burn scar does. The detector and the reference were very probably
responding to two different real phenomena in different parts of one bounding
box, rather than disagreeing about the same event. That is a more troubling
failure than a wrong number, because the output was internally coherent, carried
a plausible area, and would have been believed.

We report this unresolved rather than quietly retuning a threshold to make the
benchmark pass. The reportable result is that an evaluation harness pointed at
our own production detectors told us something we did not want to hear, which is
the entire reason to build one before you have numbers you like.

### 4.3 A model ID is not a stable resource

Our natural-language layer began returning 404s on every call. The queries were
well-formed, our key was valid, and the gateway reported no outage. The cause was
three layers down: the model we had pinned, Claude 3.5 Haiku, had been retired
months earlier, and the only provider on our gateway still advertising it served
a deprecated end-of-life snapshot that 404'd every request.

It took four attempts to fix, and the sequence is the lesson. We first routed
around the bad provider with a denylist. That appeared to work and did not: our
model identifier let requests slip past the ignore-list back to the same dead
backend. We then switched to a positive pin naming the first-party provider only,
which worked. Finally we accepted the actual diagnosis, which was not a routing
problem at all: the model was gone. We moved to Haiku 4.5 and deleted the
provider pinning entirely, because a current model needs none.

Two things follow. The abstraction that makes a multi-provider gateway
convenient, that you name a model and someone serves it, is the same abstraction
that hid a dead backend from us. And denylisting providers is a fragile reflex:
pin positively, and treat provider-level 404s as a distinct alarm from your own
bugs, because they look nothing alike in a stack trace and we spent our first
hours looking in our own code.

A related failure recurred while preparing this report. Our shared model budget
was exhausted, and the only symptom was that natural-language queries began
failing for every user with a 402 the frontend surfaced as a generic error.
Nothing alerted us; we found it while running an evaluation.

### 4.4 A status indicator we redesigned into being unable to say "broken"

Users intermittently saw the app report the API as offline when it was merely
cold-starting: Cloud Run scaled to zero, and the container blocked on Earth
Engine's initialization before it could answer a health check. Our first fix
added a "waking up" state to the status badge, which was worse than the bug. It
never timed out, so a genuine outage became indistinguishable from a cold start,
and we had built a UI that could no longer express "actually broken." We deleted
the state. The real fix was architectural: initialize Earth Engine on a
background thread, answer health checks immediately, and have only the routes
that touch Earth Engine wait on a readiness handshake. We had reached for a UI
state to describe a backend problem, and adding vocabulary to the symptom cost us
the ability to report the disease.

### 4.5 An asynchronous job system we built and never needed

Our first version ran every analysis inside the request cycle, and large areas
pushed past reasonable timeouts. We built a Redis-backed queue with a separate
worker process and a status-polling endpoint, and along the way a good bug: the
worker silently failed until we realized it must initialize Earth Engine itself,
because it does not share memory with the API server that queued the job.

None of this runs in production. The deployed path is synchronous by design:
Earth Engine calls block, so FastAPI runs them in its threadpool, and the latency
problem was solved by moving initialization off the startup path and eliminating
cold starts. The queue remains in the codebase, optional, behind a transparent
synchronous fallback.

Measured latency supports that and contradicts our own advertised estimates in
both directions. Each registry entry carries an `estimated_seconds` shown to the
user before they commit to a run. Against fixed city-scale areas:

| Analysis | First request | Cached repeat | Advertised |
|---|---|---|---|
| Ship detection | 1.6 s | 0.7 s | 30 s |
| Oil spill | 1.8 s | 1.1 s | 25 s |
| Urban growth | 5.6 s | 1.1 s | 25 s |
| Flood extent | 19.2 s | 2.5 s | 20 s |
| Wildfire burn scar | 48.5 s | 3.3 s | 20 s |
| Deforestation | 82.6 s | 3.0 s | 30 s |

Simple single-baseline detectors return an order of magnitude faster than
promised. The two using multi-threshold ensembles run 2.4x and 2.75x longer than
promised on a first request. Once Earth Engine has cached a computation graph,
any type returns in under 4 s regardless of complexity. The estimates were
written once when each analysis was added and never measured.

### 4.6 An unattended background job spending a shared budget

An autonomous sweeper runs every six hours, analyzing active disaster zones and a
rotating watchlist to populate a public feed, and calls the language model to
narrate each finding. It is enabled by default and starts ninety seconds after
every container boot. No user action is required, and no alarm distinguishes its
spend from user-driven spend. It was a contributing cause of the budget
exhaustion in Section 4.3. An agentic process that costs money on a timer needs
its own budget accounting from the day it is written, not after it drains a
shared pool.

### 4.7 One smaller admission

We left our database in open test mode, with no security rules, through most of
development. That is the right default for early velocity, but it auto-expires
and is easy to forget before opening a tool to people outside the team.

## 5. Deployment Status

Kairos has not been publicly released or promoted. Its usage comes entirely from
targeted outreach: cold contact with researchers, and demonstrations to people we
have worked with in our lab. Over the 30 days preceding submission it received
123 unique visitors and 12 sign-ups to the Janus early-access list. Janus itself
is gated behind individually issued access codes.

We describe this as early, deliberately narrow deployment. The users are a
relevant technical audience rather than a general-public sample, and the volume
does not support reliability claims from usage patterns. The accuracy figures in
Section 3 come from the validation harness, independent of usage.

Feedback clustered on two points worth reporting. Two users independently asked
for capabilities beyond current scope in the same direction: importing their own
commercially licensed imagery to analyze alongside Sentinel-1, and extending our
hazard-outlook feature into forward prediction months ahead. Both are requests to
move from describing what the record shows toward forecasting, the boundary we
have been most careful not to cross silently, and we read them as evidence that
boundary is not visible enough in the product.

A third reported the interface itself as the main confusion: a chat box, a map,
and a sidebar wizard operating on the same task, without it being obvious how
they composed, resolved for him only by the built-in tutorial. We take this as a
real qualification of the design decision in Section 3. Routing both entry points
through one schema is defensible engineering and we would do it again for the
debuggability alone, but the user-facing consequence is more surfaces than a new
user can immediately place, and it took a tutorial rather than the design being
self-evident.

## 6. Conclusion

Kairos's premise is that the barrier between public SAR data and the people who
could use it is mostly an interface problem. What we learned is that the
interface problem is really a trust problem: a language model in front of a
scientific instrument makes the tool reachable and simultaneously makes it easier
to be confidently wrong, and most of our engineering ended up on that second
half. Both of our sharpest findings are the same thing, a component producing
fluent, internally coherent, wrong output that no amount of using the product
would have surfaced.

Two lessons generalize past our domain. Anything a model is told about your
system should be generated from the same source of truth the rest of the system
reads, because a hand-maintained description will drift and then defend the drift
fluently. And an evaluation harness is worth building before you have numbers you
like: ours reported zero agreement on a detector we believed worked, which is
uncomfortable and is the entire value. Our next steps run the same direction:
widening the validation suite so more of what we ship is measured rather than
asserted, and making the boundary between measurement and prediction visible
enough that users stop asking us to cross it.

---

## References

DeVries, B.; Huang, C.; Armston, J.; Huang, W.; Jones, J. W.; and Lang, M. W.
2020. Rapid and robust monitoring of flood events using Sentinel-1 and Landsat
data on the Google Earth Engine. *Remote Sensing of Environment*, 240: 111664.

Gorelick, N.; Hancher, M.; Dixon, M.; Ilyushchenko, S.; Thau, D.; and Moore, R.
2017. Google Earth Engine: Planetary-scale geospatial analysis for everyone.
*Remote Sensing of Environment*, 202: 18–27.

Tellman, B.; Sullivan, J. A.; Kuhn, C.; Kettner, A. J.; Doyle, C. S.;
Brakenridge, G. R.; Erickson, T. A.; and Slayback, D. A. 2021. Satellite imaging
reveals increased proportion of population exposed to floods. *Nature*, 596:
80–86.

Torres, R.; Snoeij, P.; Geudtner, D.; Bibby, D.; Davidson, M.; Attema, E.; et al.
2012. GMES Sentinel-1 mission. *Remote Sensing of Environment*, 120: 9–24.
