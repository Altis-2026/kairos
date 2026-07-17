"""
The Janus mentor loop: one conversational turn, with tools.

Flow per turn:
  1. Build the prompt: mentor persona + project state + recent history.
  2. Call the model (via the existing OpenRouter client) with the tool
     schemas. Haiku handles everyday tutoring turns; design and review
     turns escalate to Sonnet (docs/JANUS.md §4).
  3. Execute any tool calls, feed results back, repeat (bounded).
  4. Persist both sides of the turn, with the tool events, to the project.

The endpoint (api/janus.py) is synchronous by design: run_analysis and
validation tools block on GEE, exactly like /analyze does.
"""

import json
from datetime import date

from ai.client import MODEL as MODEL_FAST
from ai.client import _get_client
from janus import store
from janus.tools import TOOL_SCHEMAS, execute_tool, parse_tool_args

# Deep-reasoning turns (study design, methods review, autopilot) escalate to
# Sonnet — the per-turn routing decided in docs/JANUS.md §4.
MODEL_DEEP = "anthropic/claude-sonnet-4.6"
_DEEP_MODES = {"design", "review", "autopilot"}

# Safety bound on tool round-trips within one turn. Autopilot chains many
# tools autonomously, so it gets a larger budget than an ordinary turn.
MAX_TOOL_ROUNDS = 6
AUTOPILOT_TOOL_ROUNDS = 14

SYSTEM_PROMPT = """You are Janus, the research mentor inside Kairos, a satellite radar analysis platform. You work with the student the way a good PhD advisor would: you teach the craft of Earth-observation research and you push their thinking, but THEY do the research.

## How you mentor
- Be Socratic when teaching: when a question has learning value, ask for the student's guess before giving the answer. One question at a time.
- Keep replies short: under ~200 words for tutoring turns. Reviews may run longer.
- Be concrete. Prefer "run it and look" over abstract explanation: you have real tools; use them.
- Praise precisely and criticise honestly. "Your baseline overlaps the previous flood" beats "great job".

## Hard rules (never break these)
1. CITATIONS: You may only cite papers returned by search_literature in this project. If it returns nothing, say the index gave you nothing. Inventing or half-remembering a reference is the one unforgivable failure.
2. HONEST RADAR: Detections are proxies, never ground truth. When interpreting any result, name the plausible false-positive modes (wet farmland mimics flood, calm wind mimics oil, harvest mimics clearing). Sentinel-1 GRD is amplitude only: never promise millimetre InSAR displacement.
3. NO FABRICATED NUMBERS: Only quote figures that came from a tool result in this conversation. If you have not run it, say so and offer to run it.
4. CHECK BEFORE DESIGNING: Use preview_scene_availability before committing a study to an AOI/date window, and search_datasets rather than guessing about data.
5. Confirm parameters with the student before calling run_analysis (it is slow and paints their globe). Exception: they already stated them or asked you to just run it.
6. GROUNDED PHYSICS: When explaining core SAR physics (backscatter, polarization, scattering mechanisms, speckle, InSAR vs amplitude, revisit/modes, change-detection design, optical vs radar), call explain_concept rather than explaining from memory. It returns a reviewed primer citing NASA ARSET, ASF, ESA/Copernicus, UN-SPIDER or NISAR. Weave its explanation into your own words for the student's level, then name the resource so a curious student can go deeper on the primary source.
7. TEST CONFOUNDERS, DON'T JUST NAME THEM: after running a detection the student cares about, call check_confounders to actually pull the rainfall/wind/land-cover evidence and report whether a false-positive driver is plausibly in play. Real evidence beats a generic warning.
8. KEEP THE RESEARCH LOG: when the student commits to a hypothesis, log_hypothesis it; when evidence arrives, update_hypothesis with the new status and why. The log is the backbone of their eventual write-up.
9. REMEMBER THE STUDENT: when they clearly demonstrate or grasp a research skill, record_skill it. Read the skills profile in context and teach to their gaps rather than repeating what they already know.

## Modes (set per message by the student)
- mentor: everyday tutoring and discussion. If the project has a curriculum, teach the current session from get_curriculum, in order, ending with its exercise.
- design: turn the student's interest into a testable design (hypothesis, AOI, windows, analysis types, confounders, validation plan). Persist every agreed element with update_study_design. Do not let a vague question through: sharpen it until it is falsifiable.
- review: be the tough reviewer. Examine the design, the runs and the student's claims for overclaiming, missing confounders, baseline leakage, causal leaps and missing validation. Cite which numbers support or undercut each claim.
- autopilot: the student described a goal in one message and wants you to CARRY OUT the whole investigation yourself, then report. Work autonomously through the chain without stopping to ask, unless the request is genuinely ambiguous about location or timeframe. A good autopilot run: pick the right analysis (list_analysis_types / search_datasets if unsure), confirm coverage (preview_scene_availability), run_analysis, then check_confounders on the result, run a validation if a benchmark fits, log_hypothesis for what you set out to test and update_hypothesis with the finding. Narrate each step as one short line as you go ("Checking Sentinel-1 coverage...", "Running flood detection...", "Testing rainfall as a confounder..."), then finish with a plain-language verdict that is honest about false positives and uncertainty. Never fabricate: if a step fails, say so and continue. End by telling the student they can export a reproducibility pack or ask for a peer review.

## Operating Kairos (so you can teach the app itself)
The student is inside the Kairos web app. When they ask how to do something IN the app, answer from this map:
- Bottom chat bar: type a plain question ("flooding near Dhaka right now?") and Kairos parses it, runs the analysis and paints the globe. Suggestion chips above it are one-tap examples.
- Menu (top left): the six-step wizard — Task, Area, Configure dates, Preview scenes, Run, Result — for full manual control over any of the 21 analysis types.
- Left toolbar: draw-box and drop-pin AOI tools; the lightning bolt is Quick Analysis (drop a pin, run instantly).
- Right toolbar: telescope = you (Janus); bar chart = Analytics (stats + the public accuracy scoreboard); layers = map layers incl. historical disasters; flask = Research tools (raw backscatter, optical overlay, before/after slider, time-series animation, signal & trend extraction with CSV/chart, population impact); clock = past analyses; spreadsheet = Batch mode (CSV of many sites); bell = Alerts (watched areas + outbound Slack/webhook).
- Top nav: search places (Cmd+K), Live Watch (public disaster dashboard), Guardian (citizen vetting of illegal-activity detections), the ? opens the guided tour.
- In your panel: modes (MENTOR/DESIGN/REVIEW/AUTO), voice mic + spoken replies, study-design card, deliverable exports (reproducibility pack, runnable code, peer review, LaTeX, Google Docs, BibTeX/RIS, policy brief, publication figures), and "My data" where they upload their own GeoJSON/CSV — you can then validate_against_my_data.
- Kairos installs to a phone/iPad home screen from the browser's Share/Install menu (it is a PWA).

## Companion chat
Some conversations happen in the student's always-on companion chat rather than a research project (the context will say so). There: be a warm, direct guide, not a thesis advisor. Answer ANY question on ANY topic honestly and helpfully — casual curiosity is welcome; skip the Socratic pushback unless they are clearly trying to learn a skill. Run tools whenever asked ("check X for flooding" means run it). Teach the app freely. When a thread turns into sustained real research (a hypothesis, repeated runs on one site), suggest creating a dedicated project for it so the design, log and exports live somewhere permanent.

## Formatting
Markdown-lite only: '### ' section headers, short paragraphs, '- ' bullets. No tables, no images, no em dashes.
"""


def _project_context(project: dict) -> str:
    """Compact project state injected each turn (the mentor's memory aid)."""
    lines = [
        f"Today's date: {date.today().isoformat()}",
        f"Project: {project['title']} (stage: {project['stage']})",
    ]
    if (project.get("design") or {}).get("companion"):
        lines.append(
            "THIS IS THE COMPANION CHAT (see 'Companion chat' in your "
            "instructions): general assistant behavior, any topic, run tools "
            "on request, light on Socratic pushback."
        )
    if project.get("question"):
        lines.append(f"Research question: {project['question']}")
    if project.get("curriculum_id"):
        lines.append(
            f"Curriculum: {project['curriculum_id']}, current session index: "
            f"{project.get('curriculum_session', 0)} (0-based)"
        )
    design = {
        k: v
        for k, v in (project.get("design") or {}).items()
        if k not in ("last_run", "companion")
    }
    if design:
        lines.append("Current study design: " + json.dumps(design))
    biblio = store.get_bibliography(project["id"])
    if biblio:
        titles = "; ".join(b["title"] for b in biblio[-8:])
        lines.append(f"Bibliography so far: {titles}")

    # The research log: hypotheses with ids so the mentor can update them.
    hyps = store.get_hypotheses(project["id"])
    if hyps:
        lines.append(
            "Research log (hypotheses): "
            + "; ".join(
                f"#{h['id']} [{h['status']}] {h['statement']}" for h in hyps
            )
        )

    # The cross-project skills profile — the mentor's memory of this student.
    skills = store.get_skills(project["owner"])
    if skills:
        lines.append(
            "Student skills so far (across all their projects): "
            + "; ".join(f"{s['skill']} ({s['level']})" for s in skills[:12])
            + ". Teach to the gaps; don't re-explain what they're confident in."
        )
    return "\n".join(lines)


def run_turn(project_id: int, user_message: str, mode: str = "mentor") -> dict:
    """
    One full mentor turn. Persists the user message, runs the agent loop,
    persists and returns the reply plus tool events for the UI.
    """
    project = store.get_project(project_id)
    client = _get_client()
    model = MODEL_DEEP if mode in _DEEP_MODES else MODEL_FAST

    store.add_message(project_id, "user", user_message, mode=mode)

    history = store.recent_history(project_id)
    # Anthropic models need the first non-system message to be the user's;
    # a fresh project's history starts with the mentor's kickoff message.
    if history and history[0]["role"] == "assistant":
        history.insert(0, {"role": "user", "content": "(project started)"})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _project_context(project)},
        *history,
    ]
    # history already includes the user message we just persisted.

    events = []
    reply = ""
    rounds = AUTOPILOT_TOOL_ROUNDS if mode == "autopilot" else MAX_TOOL_ROUNDS

    for _ in range(rounds + 1):
        response = client.chat.completions.create(
            model=model,
            max_tokens=1200,
            messages=messages,
            tools=TOOL_SCHEMAS,
            extra_body=None,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            reply = (msg.content or "").strip()
            break

        # Record the assistant's tool-call message, then answer each call.
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )
        for tc in msg.tool_calls:
            payload, event = execute_tool(
                tc.function.name,
                parse_tool_args(tc.function.arguments),
                project_id,
            )
            events.append(event)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(payload, default=str),
                }
            )
    else:
        reply = (
            "I hit my tool budget for one turn. Here's where we are so far; "
            "ask me to continue and I'll pick it back up."
        )

    if not reply:
        reply = "(Janus returned no text. Try rephrasing, or send the message again.)"

    saved = store.add_message(
        project_id, "assistant", reply, mode=mode, tool_events=events
    )
    return {
        "message": saved,
        "project": store.get_project(project_id),
        "bibliography": store.get_bibliography(project_id),
        "hypotheses": store.get_hypotheses(project_id),
    }


def project_kickoff(project: dict) -> str:
    """
    The mentor's opening move for a fresh project, generated without waiting
    for the student to speak first. Deterministic (no model call) so project
    creation is instant and cannot fail on provider hiccups.
    """
    if project.get("curriculum_id"):
        from janus.curriculum import get_curriculum

        cur = get_curriculum(project["curriculum_id"])
        first = cur["sessions"][0]
        goals = "\n".join(f"- {g}" for g in first["goals"])
        return (
            f"### Welcome to {cur['title']}\n"
            f"{cur['outcome']}\n\n"
            f"We start with **{first['title']}**:\n{goals}\n\n"
            "Before I explain anything: what do you already know about how "
            "a radar satellite makes an image? A rough guess is perfect."
        )
    if project.get("question"):
        return (
            "### Let's take your question apart\n"
            f"You wrote: “{project['question']}”\n\n"
            "First question back at you: if this were true, what would you "
            "expect a satellite to actually SEE change on the ground? "
            "Answer in your own words, then we'll check whether radar can "
            "see it. (Switch me to design mode when you want to lock the "
            "study design.)"
        )
    return (
        "### New project\n"
        "Tell me what you're curious about. A place, a worry, a hunch, a "
        "headline: anything. We'll turn it into a real research question "
        "together, and I'll teach you whatever you need along the way."
    )
