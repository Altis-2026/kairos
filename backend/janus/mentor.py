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

# Deep-reasoning turns (study design, methods review) escalate to Sonnet —
# the per-turn routing decided in docs/JANUS.md §4.
MODEL_DEEP = "anthropic/claude-sonnet-4.6"
_DEEP_MODES = {"design", "review"}

# Safety bound on tool round-trips within one turn.
MAX_TOOL_ROUNDS = 6

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

## Modes (set per message by the student)
- mentor: everyday tutoring and discussion. If the project has a curriculum, teach the current session from get_curriculum, in order, ending with its exercise.
- design: turn the student's interest into a testable design (hypothesis, AOI, windows, analysis types, confounders, validation plan). Persist every agreed element with update_study_design. Do not let a vague question through: sharpen it until it is falsifiable.
- review: be the tough reviewer. Examine the design, the runs and the student's claims for overclaiming, missing confounders, baseline leakage, causal leaps and missing validation. Cite which numbers support or undercut each claim.

## Formatting
Markdown-lite only: '### ' section headers, short paragraphs, '- ' bullets. No tables, no images, no em dashes.
"""


def _project_context(project: dict) -> str:
    """Compact project state injected each turn (the mentor's memory aid)."""
    lines = [
        f"Today's date: {date.today().isoformat()}",
        f"Project: {project['title']} (stage: {project['stage']})",
    ]
    if project.get("question"):
        lines.append(f"Research question: {project['question']}")
    if project.get("curriculum_id"):
        lines.append(
            f"Curriculum: {project['curriculum_id']}, current session index: "
            f"{project.get('curriculum_session', 0)} (0-based)"
        )
    design = project.get("design") or {}
    if design:
        lines.append("Current study design: " + json.dumps(design))
    biblio = store.get_bibliography(project["id"])
    if biblio:
        titles = "; ".join(b["title"] for b in biblio[-8:])
        lines.append(f"Bibliography so far: {titles}")
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

    for _ in range(MAX_TOOL_ROUNDS + 1):
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
