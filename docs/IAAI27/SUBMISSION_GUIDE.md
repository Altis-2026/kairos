# IAAI-27 Submission Guide

Everything left between `REPORT_FINAL.md` and a submitted PDF.

---

## 1. Page count: measure, then trim from this list

`REPORT_FINAL.md` is roughly 3,390 words of body text plus three tables.
Estimated at 3.9 pages without a figure, 4.25 with one. **That estimate is
approximate and only the real AAAI template can settle it.** Compile first, look
at the actual page count, then act:

| Compiled length | Do this |
|---|---|
| Under 3.6 pages | Add the architecture figure (Section 2 below) |
| 3.6 to 4.0 pages | Ship without the figure. It is optional; the limit is not |
| Over 4.0 pages | Trim in the order below until you fit |

**Trim order.** Each item is the next-least-load-bearing thing in the paper.
Cut from the top; stop as soon as you fit.

1. **Section 4.7** (open database test mode, 45 words). Weakest failure.
2. **Section 3's "Refusing rather than guessing"** paragraph (85 words). Cut to
   one sentence: the flood consensus refuses to run below 20% cloud-free optical
   coverage, because a consensus of one method is not a consensus.
3. **The ship-detection benchmark paragraph** in Section 3 (60 words). It has no
   numbers yet, which makes it the weakest content in an otherwise measured
   section.
4. **Latency table rows** (Section 4.5). Keep flood, wildfire, deforestation;
   drop ship, oil, urban growth. The prose already states the range.
5. **Section 2's frontend paragraph** (30 words). Fold into the backend one.
6. **Section 4.4** (status indicator, 120 words). A real lesson, but the least
   unique of the failures.

Do **not** trim, at any page count: Section 4.1, Section 4.2, the accuracy table,
Section 5, or "One schema, two front doors" in Section 3. Those are what the
track scores.

---

## 2. The architecture figure

Optional. Build it only if Section 1's page count allows.

### What it must show

Not a generic four-box stack. The load-bearing idea is that **two entry paths
converge on one schema before anything reaches Earth Engine**, because that
convergence is the paper's argument and the reason Section 4.1 was findable.

```
   ┌──────────────┐          ┌──────────────┐
   │ Sidebar      │          │ Chat         │
   │ wizard       │          │ "flooding    │
   │ (click AOI,  │          │  near Dhaka" │
   │  pick type)  │          │              │
   └──────┬───────┘          └──────┬───────┘
          │                         │
          │                    ┌────▼─────────┐
          │                    │ LLM parser   │
          │                    │ Haiku 4.5    │
          │                    └────┬─────────┘
          │                         │
          └───────────┬─────────────┘
                      ▼
        ┌─────────────────────────────┐
        │  ONE STRUCTURED SCHEMA      │   <- the point of the figure
        │  analysis_type, bbox,       │
        │  start_date, end_date       │
        └─────────────┬───────────────┘
                      ▼
        ┌─────────────────────────────┐
        │  Analysis registry          │
        │  22 entries, one dict       │
        └─────────────┬───────────────┘
                      ▼
        ┌─────────────────────────────┐
        │  Google Earth Engine        │
        │  server-side, nothing       │
        │  downloaded                 │
        └─────────────┬───────────────┘
                      ▼
              tile URL + stats
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Mapbox globe               │
        └─────────────────────────────┘
```

Two annotations earn their space. Put a small note on the wizard arrow reading
"reads the registry directly," and one on the parser arrow reading "reads a
hand-maintained prompt (Section 4.1)." That single contrast is the whole finding,
rendered visually.

### How to actually make it

Easiest to hardest, pick one:

- **draw.io / diagrams.net** (free, browser, no install). Build the boxes, then
  File > Export as > PDF with "Crop to content" checked. Vector, so it stays
  sharp at any zoom, which is what "high-resolution PDF" in the call requires.
- **Google Slides.** One slide, resize to roughly 6 x 4 inches, then File >
  Download > PDF. Fine, and faster if you already know it.
- **PowerPoint / Keynote**, same approach.

Rules regardless of tool: no colour that carries meaning on its own (some
reviewers print greyscale), font no smaller than 8pt at final printed size, and
export vector PDF rather than PNG so nothing pixelates.

In LaTeX, place it as a single-column figure near Section 2:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{architecture.pdf}
\caption{Both entry paths resolve to one structured schema before any
computation runs. The wizard builds it from the analysis registry directly;
the language layer builds it from a hand-maintained system prompt, which is
where the failure in Section 4.1 originated.}
\label{fig:arch}
\end{figure}
```

---

## 3. Requirements compliance

Checked line by line against the IAAI-27 call.

### Hard gates

| Requirement | Status |
|---|---|
| Track 3b, Experience Report | Select explicitly on the OpenReview form |
| 2 to 4 pages | **Verify after compiling.** See Section 1 |
| AAAI two-column, **CameraReady** template | Download from aaai.org/authorkit27. Not the anonymous variant, not an older year's `.sty` |
| US Letter, 8.5 x 11 | Template default; confirm in the PDF properties |
| High-resolution, trouble-free PDF | Vector figure, fonts embedded (Type 1 or TrueType) |
| Identifying author info present (single-blind) | Amogh Vinaykumar, affiliation, contact email. **Affiliation still needed** |
| Authors from the deploying organization | You are the deploying organization. The report says so in first person throughout |
| Self-contained without supplement | Yes. Nothing in the argument requires the repo |
| Originality | Congressional App Challenge is not a refereed venue, so no conflict. Read the form's exact wording yourself before affirming |
| Submitted via OpenReview | The only accepted channel |
| References uncounted against the limit | Four references, correctly AAAI-formatted |

### How the report answers the call's four questions

- *"What new domain or problem, and why hard?"* Section 1. The non-obvious
  framing, that the hard part was not the radar, is what makes it a report rather
  than a description.
- *"What technical approach, what design decisions and alternatives?"* Sections 2
  and 3, plus three genuinely abandoned approaches named as abandoned: the
  provider denylist (4.3), the async job queue (4.5), and the "waking up" UI
  state (4.4). The call rewards abandoned approaches explicitly.
- *"What impact, and how measured?"* Section 3's accuracy table, Section 4.1's
  85% to 92.5%, Section 4.5's latency table, Section 5's usage. Measured, with
  methods stated, and none of it rounded up.
- *"What went wrong on the way to deployment?"* Section 4, six failures, all
  first-person and traceable.

### Track 3b topic areas hit

- **Path to Responsible Deployment** (evaluation harnesses, pre-deployment
  safety cases): the validation harness, the public scoreboard, confounder
  screening, the consensus refusal path.
- **What Went Wrong and Why** (failure modes specific to generative systems):
  Section 4 throughout. 4.1 is a genuine generative-system failure class, a model
  fluently defending a stale description of its own system.
- **Deployment Economics and Efficiency** (cost and latency, model routing): the
  latency table, per-turn Haiku/Sonnet routing, and the budget-exhaustion
  incident in 4.3 and 4.6.
- **Operating AI Systems in Production** (guardrails, tracing of agentic
  systems): Janus's bounded tool loop and the access gate.

Four solid hits. Do not stretch for the other three areas; under a rubric
weighted to "usefulness and candor," four real ones beat seven thin ones.

---

## 4. Remaining steps, in order

1. **Affiliation line.** The last placeholder. Search `REPORT_FINAL.md` for `[[`.
2. **Download the AAAI-27 Author Kit** from aaai.org/authorkit27. Use the
   CameraReady template. This is the single most common cause of desk rejection.
3. **Move the content in.** Title into `\title{}`, author into `\author{}`,
   abstract into the abstract environment, each numbered section into
   `\section{}`. The three Markdown tables become `tabular`.
4. **Compile and check the page count.** Act on Section 1's table.
5. **Figure**, if the page count allows.
6. **Read the compiled PDF once, start to finish**, specifically for anything
   that reads as overclaiming. The register you want is already in Section 5;
   keep it everywhere.
7. **One outside reader.** Ask them one question: does Section 4 read as genuine
   or as a checkbox exercise? That is the section the track scores hardest.
8. **Search the compiled PDF for `[`** to confirm no placeholder survived.
9. **Verify fonts are embedded.** In Acrobat: File > Properties > Fonts. Every
   entry should say "Embedded" or "Embedded Subset."
10. **Register on OpenReview**, confirm you are submitting to IAAI-27 and not the
    AAAI-27 main track, select Track 3b, add keywords (natural-language
    interfaces, deployed tools, Earth observation, agentic systems, evaluation).
11. **Submit with real margin** before 11:59 PM AoE, 8 September 2026, and
    confirm the receipt email arrives.

Dates after that: notification 30 October, conditional revisions 24 November,
camera-ready 14 December, conference 18 to 20 February 2027 in Montreal.

---

## 5. Repository hygiene, if you link the repo

Reviewers are not obliged to open it, but some will.

- [ ] **`CLAUDE.md` is stale and contradicts the code.** It states the Anthropic
      API and `claude-sonnet-4-6` (the code uses OpenRouter with Haiku 4.5), six
      analysis types (there are 22), and a file tree missing `janus/` and
      `watch/`. It is the second file a curious reviewer opens. Fix it or remove
      it before linking.
- [ ] Confirm no secrets in git history. Commit `97e4923` mentions a rotated
      OpenRouter key; make sure the old one is not sitting in an earlier commit.
- [ ] Confirm `kairos_waitlist.db` and `kairos_scoreboard.db` are gitignored and
      never committed, since the waitlist holds real email addresses.
- [ ] The scoreboard writes SQLite to Cloud Run's ephemeral disk. If you cite the
      public scoreboard URL anywhere, a container restart will show a reviewer an
      empty table. Either move it to Firestore or do not cite the live URL.

---

## 6. Known gaps, stated plainly

Things a reviewer could reasonably raise that you should be ready to answer, and
that the paper already concedes rather than hides:

- **The accuracy numbers are weak.** IoU 0.214, 0.0, and 0.017. The paper reports
  them as they came back and explains the fire result. That is the right call for
  this track, and it is why Section 4.2 exists.
- **The Rondônia result is unexplained.** The paper reports 0.017 without a
  diagnosis, unlike the fire result. If you have time before the deadline, the
  same investigation that explained the fire (compare detection against the
  reference visually, check the optical agreement figure) would likely explain
  this one too, and a second diagnosis would strengthen Section 4.2.
- **Usage is small and narrow.** 123 visitors, no public release. Section 5 says
  this plainly and scopes every claim to it.
- **The ship benchmark has no results.** Built, not yet run, and labelled that
  way. Running it requires downloading the AIS slice via
  `tools/get_ais_case.py`, and Cloud Run's ephemeral disk means it will not
  persist server-side, so run it locally if you want the number.
