# IAAI-27 Experience Report — Gap Analysis

What the draft says, what the codebase actually contains, and what only you can fill in.
Written against commit `5c9542d` (2026-08-01).

---

## 1. The strategic problem with the current draft

The draft is a competent "we built a SAR web app" report. The codebase is a
much stronger paper than that, and the draft is leaving the strongest material
on the floor.

IAAI-27's call names, as topics of *special interest*:

- "deployed applications of large language models and foundation models,
  **including agentic systems in production**"
- "**evaluation and assurance of AI systems in deployment**"
- "the **economics** of operating AI at scale"
- Track 3b areas: "**What Went Wrong and Why** … failure modes specific to
  generative and agentic systems"

Kairos has real, shipped machinery in **every one of those four buckets** —
and the draft mentions none of them:

| IAAI topic | What's actually in the repo | In draft? |
|---|---|---|
| Agentic systems in production | **Janus**: `backend/janus/`, 21 callable tool schemas in `tools.py`, a bounded tool loop (`MAX_TOOL_ROUNDS=6`, `AUTOPILOT_TOOL_ROUNDS=14`), 4 modes, autonomous "autopilot" mode that chains analyses unattended | ❌ absent |
| Evaluation & assurance | `gee/validation.py` — re-runs the **production detector** against Global Flood DB / MCD64A1 / Hansen and computes IoU, precision, recall, F1 live; `scoreboard.py` publishes every run ever made at `GET /scoreboard` | ❌ absent |
| Guardrails against generative failure | The Janus system prompt's hard rules (no fabricated citations, no fabricated numbers, mandatory confounder testing); `gee/confounders.py` turns a *verbal* warning into a *measured* one using CHIRPS/ERA5/WorldCover | ❌ absent |
| Deployment economics | Per-turn model routing: Haiku 4.5 for tutoring, Sonnet 4.6 escalation for design/review/autopilot (`janus/mentor.py:26`) | ❌ absent |
| What went wrong | See §3 — the git history has sharper failures than the draft's three | ⚠️ weaker ones used |

**Recommendation:** re-frame the report. Not "we put a chat box on Earth
Engine," but: *when you put a language model in front of a scientific
instrument, the hard part is stopping it producing confident nonsense — here
is the machinery we built for that, and here is what broke.* That framing is
directly on two named topics of special interest, and it is a paper only a
team that actually deployed something can write.

---

## 2. Technical claims in the draft that are now WRONG

Checklist item 4 says to verify every technical claim still describes the
codebase. Four don't.

### 2.1 "Anthropic API" → it's OpenRouter
The draft (and `CLAUDE.md`) say the Anthropic API with `claude-sonnet-4-6`.
Reality (`backend/ai/client.py`): the OpenAI SDK pointed at
`https://openrouter.ai/api/v1`, model `anthropic/claude-haiku-4.5`, with
`anthropic/claude-sonnet-4.6` for deep Janus turns.

This matters beyond pedantry — the gateway indirection *is* the cause of your
best failure story (§3.1). Fix the claim and you gain a section.

### 2.2 "Asynchronous jobs over synchronous requests" → backwards
The draft presents the Redis queue as a shipped design decision, and the
worker's GEE-init bug as the centrepiece failure.

Reality:
- `jobs/queue.py` docstring: "Optional in development … if Redis is not
  running, the API transparently falls back to synchronous execution."
- `api/analyze.py` docstring: "GEE calls are blocking, so this endpoint is
  **intentionally synchronous** (`def`, not `async def`) — FastAPI runs it in
  a threadpool."
- `janus/mentor.py`: "The endpoint is synchronous by design."
- Commit `444f47c`: "Set Cloud Run min-instances to 1 to eliminate cold starts."

So the deployed system does **not** use the queue. The latency problem was
actually solved by (a) FastAPI's threadpool, (b) moving GEE init off the
startup path into a background thread with a `gee_ready` handshake
(`main.py:_init_gee_in_background`), and (c) `min-instances=1`.

**This is a better story than the one in the draft**, and it's an honest one:
*we built the async infrastructure, and then the real fix turned out to be
somewhere else entirely.* Abandoned approaches are explicitly rewarded by this
track. But the draft currently claims we shipped it, which is not true.

### 2.3 "Six analysis pipelines" → 22
`ANALYSIS_REGISTRY` has 22 entries. Don't pad the paper with a list of all 22 —
but "six" understates the registry-driven architecture, which is a genuine
design contribution (add one dict entry, the frontend rebuilds itself from
`GET /registry`; nothing else changes).

### 2.4 Hosting
Draft implies Firebase Hosting. `main.py` CORS and the README point at
`https://openkairos.vercel.app`; backend is Cloud Run. Firebase is used for
auth/Firestore. Say it accurately.

### 2.5 Also unmentioned but true and paper-worthy
- `provenance.py` — every result carries a SHA-256 content hash + HMAC
  signature; `POST /verify` re-checks it. Deliberately hashes *scientific
  content only*, so restyling a report doesn't break verification but changing
  a number does.
- `stats.py` — dependency-free OLS with an exact Student-t p-value (regularized
  incomplete beta) **and** Mann-Kendall + Sen's slope.
- `gee/consensus.py` — two-instrument agreement map (S1 backscatter vs S2
  NDWI) that *refuses to run* when cloud-free optical covers <20% of the AOI,
  rather than silently returning a one-method "consensus."

That last one is a small, sharp illustration of the whole thesis: the system is
designed to decline rather than to guess.

---

## 3. Better failure stories, straight from git

The draft's three failures are real but soft. These are sharper, dated, and
traceable to commits a reviewer could check.

### 3.1 ⭐ The retired model snapshot (THE centrepiece — swap this in)

Commit trail, all 2026-06-21:
```
98e6917  Route OpenRouter calls around Amazon Bedrock's dead model snapshot
d71b2b7  Fix OpenRouter model id causing Bedrock 404s to slip past provider.ignore
9ec7a4b  Pin OpenRouter requests to Anthropic's first-party endpoint via provider.only
5bda8c3  Switch OpenRouter chat to Claude Haiku 4.5 (the live, non-retired Haiku)
```
And the comment left behind in `ai/client.py:8-12`:
> "Claude 3.5 Haiku was retired in Feb 2026; its only remaining OpenRouter
> provider was Amazon Bedrock's deprecated end-of-life snapshot, which 404s on
> every call."

Why this is the best failure in the repo for *this* track:

- It is a **failure mode specific to how LLMs are actually deployed in 2026** —
  through a gateway that abstracts away which provider serves your model. The
  abstraction that makes multi-provider routing convenient is the same
  abstraction that hid a dead backend from us.
- It took **four commits and three wrong fixes** to land: first route *around*
  the bad provider (`provider.ignore`), then discover the model ID let it slip
  past the ignore-list anyway, then pin positively with `provider.only`, then
  finally accept the model was simply retired and move to Haiku 4.5. The
  progression from denylist → allowlist → "the resource is gone" is a
  genuinely transferable lesson.
- The generalizable rule: **a model ID is not a stable resource.** Denylisting
  providers is fragile; pin positively, and monitor for provider-level 404s
  distinctly from your own bugs.

Note the final state is that `_PROVIDER_PREFS = None` — you removed the pinning
once the model was current. Say that too; "we added the workaround and then
deleted it" is candour reviewers reward.

### 3.2 ⭐ "API offline" — a user-visible failure

```
91b3477  Free fix for random 'API offline': decouple cold start from GEE init,
         self-healing status badge, keep-warm cron
7cd6bd8  Fix: WAKING UP badge never gave up on a genuine outage
286db40  Drop the "waking up" status state — just linking/active/offline
444f47c  Set Cloud Run min-instances to 1 to eliminate cold starts
```

This is the story the checklist asks for — *something that actually broke in
front of a user.* Cloud Run cold start + a blocking `ee.Initialize()` on the
startup path meant the frontend's health badge showed the API as offline while
it was merely waking. Three things worth telling:

1. The first fix (a "WAKING UP" state) **made things worse in a specific way**:
   it never timed out, so a genuine outage looked identical to a cold start.
   You had built a UI that could no longer express "actually broken."
2. The state was then *deleted* (`286db40`) — the honest fix was fewer states,
   not more.
3. The architectural fix (`main.py`) is clean and worth one sentence: init GEE
   on a background thread, expose a `gee_ready.wait()` handshake that only
   GEE-touching routes block on, so `/health` answers immediately.

### 3.3 The deploy pipeline — eight consecutive retriggers

July 19–20, in order: Artifact Registry repo missing → secrets not configured
→ Cloud Resource Manager/Firebase APIs not enabled → Firebase Hosting Admin
role → firebase-adminsdk needs Firebase Admin → regenerate `FIREBASE_SA_KEY` →
auto-create the Hosting site → pin the site ID. Plus, on 2026-08-01,
`5c9542d`: Cloud Run was running as a service account that *didn't have Earth
Engine access at all*.

This replaces the draft's vague "infrastructure ate week one" with commit-level
evidence, which is far more credible. The lesson to draw is specific: **every
one of these failed at deploy time, not at review time**, because none of them
are expressible in the code being reviewed. Permissions are invisible to your
test suite.

### 3.4 The agent that wrote base64 into a YAML file
`bd4cbaa`: "Fix deploy.yml: previous commit accidentally wrote base64-encoded
content instead of raw YAML, which broke the workflow entirely."

Optional, but this is a *very* current failure mode (an AI coding agent
producing plausible-looking but structurally wrong output in a file nothing
type-checks) and IAAI reviewers will find it interesting. Include it only if
you're comfortable stating that the codebase was substantially built with an
AI coding agent — which, given ~30 commits on `claude/*` branches in the public
repo history, a reviewer clicking through will notice anyway. **Better to own
it than to have it discovered.**

### 3.5 Keep from the draft
- The open Firestore test-mode rules. Short, honest, real.
- The frozen-release-vs-live-product lesson. Good, keep as-is.
- Drop or demote the worker GEE-init bug (§2.2) — it's a bug in code that never
  shipped.

---

## 4. Numbers you can honestly report — and where to get them

The checklist is right that this is the highest-value gap. Here's the good
news: **you built a measurement system, you just haven't run it.**

### 4.1 Run the benchmarks and quote the results (do this first)
`gee/validation.py` has three wired benchmarks:

| id | analysis | reference |
|---|---|---|
| `bangladesh-monsoon-2017` | flood_extent | Global Flood Database, 250 m (Tellman et al. 2021) |
| `camp-fire-2018` | wildfire_burn_scar | MODIS MCD64A1, 500 m |
| `rondonia-clearing-2020` | deforestation | Hansen GFC lossyear, 30 m |

```bash
curl -X POST $API/validation/run -H 'content-type: application/json' \
     -d '{"benchmark_id":"bangladesh-monsoon-2017"}'
# repeat for camp-fire-2018, rondonia-clearing-2020
curl $API/scoreboard
```

Run each **3–5 times**, then quote IoU / precision / recall / F1 per benchmark
from `/scoreboard`. This gives you a real accuracy table with a real
methodology and *pre-written caveats* (the module already returns them: coarser
reference, different sensor, agreement computed at the reference's native
scale).

⚠️ Two things to check before you trust the output:
- `scoreboard.py` writes to SQLite on Cloud Run's **ephemeral filesystem**
  (same known issue flagged in `api/waitlist.py`). A container restart wipes
  it. Either run all benchmarks in one session and screenshot/save the JSON, or
  run them locally. **Do not claim the scoreboard is a durable public record
  unless you move it off ephemeral disk first** — see §6.
- Confirm the Rondônia benchmark still runs; `_reference_mask` raises if the
  year exceeds `_HANSEN_LAST_YEAR = 2023`, which is fine for a 2020 window, but
  verify rather than assume.

### 4.2 Latency — measure it, don't guess
Time 5–10 runs per analysis type at a city-scale AOI and report a median and a
range. The registry already carries `estimated_seconds` per type (flood 20,
ships 30, deforestation 30) — **check whether those estimates are true.** If
they're not, say so; "our own advertised estimates were optimistic by 40%" is a
finding, not an embarrassment.

### 4.3 NL parser accuracy — cheap and high-value
Write down 30–50 real queries in the form users actually type. Run each through
`POST /query`. Score each parse on three axes: correct analysis type, correct
place, correct date window. Report as "N of 50 fully correct; the M failures
were mostly X."

This is a couple of hours of work and it directly answers the call's "how was
it measured?" — and per the checklist, a *characterized failure mode* ("it
resolves relative dates like 'last monsoon' badly") is worth more than a high
score.

### 4.4 Model routing cost — you have the numbers already
Haiku 4.5 is $1/$5 per Mtok (stated in `ai/client.py`), Sonnet 4.6 is used only
for design/review/autopilot turns. Log token counts for ~20 turns of each type
and report the actual cost delta the routing buys. That's a concrete
"economics of operating AI" data point, which is a named topic.

### 4.5 Things only you know (nobody can derive these from the repo)
- [ ] **How many real people have used it**, over what dates. Vercel Web
      Analytics was added in `756c6dc` (2026-07-18) — pull the actual number.
      Small is fine; the track has a category for it.
- [ ] **Waitlist count** — `GET /waitlist/count` (but see the ephemeral-disk
      caveat; check Cloud Logging for the durable copy).
- [ ] **Tester quotes.** The checklist's example is exactly right. Two or three
      verbatim confusion points beat any amount of "users found it intuitive."
      Specifically probe: did anyone distrust the chat parse enough to switch
      to the wizard? That would be *direct evidence* for your central design
      decision, which currently rests on an unsupported assertion.
- [ ] Author names, order, affiliation, contact email (checklist §2).

---

## 5. Structural changes to the paper

Proposed section map for 4 pages, with the current draft's sections mapped in:

1. **Introduction** — keep, tighten. (draft §1)
2. **System overview** — keep, correct per §2 above, add the registry pattern
   and one architecture figure. (draft §2)
3. **Keeping the language layer honest** — **NEW, and this is the core.**
   Structured-schema routing + Janus's hard rules + confounder screening +
   ground-truth validation + provenance. Absorbs draft §3's chat-vs-wizard
   decision, which belongs here rather than in a generic design-decisions list.
4. **What went wrong** — rebuilt on §3 above. Lead with the retired model
   snapshot. (draft §4)
5. **Early deployment and measured results** — the accuracy table from §4.1,
   latency from §4.2, parser scoring from §4.3, honest usage numbers. (draft §5)
6. **Lessons** — keep, retarget to the new failures. (draft §6)
7. **Conclusion** — keep, trim. (draft §7)

Cuts to make room: draft §3's "server-side over local processing" trade-off
compresses to three sentences inside §2 (it's the least load-bearing content
for this track, exactly as the checklist predicted), and the async-jobs
decision moves into §4 as an abandoned approach.

**Figure:** one architecture diagram. The README already has an ASCII version
that's basically correct; render it properly. Show the *two* paths into the
same schema (wizard and NL parse converging), because that convergence is the
paper's argument — a diagram that shows it is doing real work, not decoration.

### Pitch language to strip (checklist §4)
Grep the draft for: "seamless", "cutting-edge", "innovative", "powerful",
"revolutionary", "effortless". Also soften "removes that barrier" in §1 →
"lowers that barrier", and "Kairos is deployed and publicly reachable" is good
— keep that sentence exactly as it is, it's the right register.

---

## 6. Should you build anything new for the paper?

You asked. Short answer: **almost nothing.** You have more system than paper.
Adding features now costs page budget you don't have and adds claims you'd have
to verify under deadline.

Three exceptions, in priority order — all are *making existing claims true*
rather than new features:

1. **Move the scoreboard off ephemeral disk** (half a day). If you publish an
   accuracy scoreboard URL in a paper and a reviewer opens it after a container
   restart and sees zero runs, that is actively damaging. Firestore is already
   wired for auth; write validation runs there. Same fix applies to the
   waitlist. **Do this one.**
2. **A `scripts/benchmark.py`** that runs all three validation benchmarks N
   times and emits a CSV/table (an afternoon). It makes §4.1 reproducible,
   it's honest supplementary material, and it means a reviewer can regenerate
   your table. High value per hour.
3. **Wire a fourth validation benchmark** for ship detection, if a public AIS
   ground-truth window is reachable — you already have `gee/dark_vessels.py`
   fusing AIS. Only if §§1–2 are done and there's slack. Ship detection is the
   analysis reviewers will most want validated, and it's currently unmeasured.

Explicitly **do not** build before the deadline: new analysis types (22 is
already more than the paper can discuss), voice mode, the paid tiers, or
anything in `docs/JANUS.md`'s roadmap. None of it improves the report and all
of it competes for the same two weeks.

---

## 7. Repo hygiene before you link it (checklist §5)

A reviewer who clicks through will land on `README.md`, which is currently
strong and honest — good. But:

- [ ] `CLAUDE.md` is **stale and contradicts the code**: it says Anthropic API
      + `claude-sonnet-4-6`, six analysis types, and a file structure that no
      longer matches (`gee/` has 30 modules, `janus/` and `watch/` are absent
      from the tree it documents). It's the second file a curious reviewer
      opens. Update it.
- [ ] The README says "22 SAR & optical analyses" — verified, the registry has
      exactly 22. Good, leave it.
- [ ] Check `backend/data/` and any `.db` files aren't committed with real
      user emails in them (`kairos_waitlist.db`, `kairos_scoreboard.db` — they're
      gitignored, confirm that's holding).
- [ ] Confirm `PROVENANCE_SECRET`, `OPENROUTER_API_KEY` and the GEE credentials
      are not in git history. `97e4923` mentions a *rotated* OpenRouter key —
      make sure the old one isn't sitting in an old commit.
- [ ] The commit history makes heavy AI-agent involvement obvious. Decide
      deliberately how you present that (see §3.4) rather than letting a
      reviewer infer it.

---

## 8. Open questions for the team

Answer these before the rewrite is final; they change the text materially.

1. Do you have any real usage numbers at all (Vercel Analytics, waitlist)? If
   the honest answer is "a handful of testers, no organic users," the paper
   should say that plainly in §5 and lean harder on the engineering lessons.
2. Are you willing to state that Kairos was built substantially with an AI
   coding agent? It's defensible and topical, but it should be a decision.
3. Is Janus actually reachable by a user today, or is it gated behind the
   waitlist / paid tiers described in `docs/JANUS.md`? This determines whether
   it's "deployed" or "built but not released" — and the paper must not blur
   that line.
4. Has anyone outside the four of you run a query end to end? The claim "works
   end to end for a cold user with no onboarding" in draft §5 needs at least
   one real cold user behind it.
