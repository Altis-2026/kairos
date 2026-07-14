"""
Janus mentor API.

  GET    /janus/status                  is the mentor available (API key set)?
  GET    /janus/entitlements?owner=     the owner's plan + unlocked features
  GET    /janus/curricula               teaching tracks
  POST   /janus/projects                create a project (+ mentor kickoff)
  GET    /janus/projects?owner=         list my projects
  GET    /janus/projects/{id}           project + messages + bibliography + insights
  PATCH  /janus/projects/{id}           rename / edit question / stage
  DELETE /janus/projects/{id}           delete a project
  POST   /janus/projects/{id}/chat      one mentor turn (may run GEE tools)
  POST   /janus/projects/{id}/watch     toggle proactive monitoring (+ instant check)
  GET    /janus/projects/{id}/pack      download the reproducibility pack (Markdown)
  POST   /janus/insights/{id}/dismiss   dismiss a proactive insight

Synchronous handlers throughout: mentor turns can invoke blocking GEE calls,
so FastAPI must run them in its threadpool (`def`, not `async def`).

Ownership is an honesty check, not security: `owner` is the Firebase uid or
an anonymous browser id. Real auth arrives with the paid tier.
"""

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from janus import (
    entitlements,
    notebook,
    proactive,
    reproducibility,
    review_report,
    store,
)
from janus.curriculum import curricula_summary
from janus.mentor import project_kickoff, run_turn

router = APIRouter()


class CreateProjectRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=120)
    question: str = Field(default="", max_length=1000)
    curriculum_id: str | None = None


class UpdateProjectRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=120)
    question: str | None = Field(default=None, max_length=1000)
    stage: str | None = None


class ChatRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    mode: str = Field(default="mentor", pattern="^(mentor|design|review)$")


class WatchRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    watch: bool


def _owned_project(project_id: int, owner: str) -> dict:
    try:
        project = store.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if project["owner"] != owner:
        raise HTTPException(status_code=403, detail="Not your project.")
    return project


@router.get("/janus/status")
def janus_status():
    return {"available": bool(os.getenv("OPENROUTER_API_KEY"))}


@router.get("/janus/entitlements")
def get_entitlements(owner: str = Query(..., min_length=1, max_length=128)):
    ent = entitlements.entitlements(owner)
    ent["unread_insights"] = store.unread_insight_count(owner)
    ent["skills"] = store.get_skills(owner)
    return ent


@router.get("/janus/curricula")
def get_curricula():
    return {"curricula": curricula_summary()}


@router.post("/janus/projects")
def create_project(request: CreateProjectRequest):
    if request.curriculum_id is not None:
        valid = {c["id"] for c in curricula_summary()}
        if request.curriculum_id not in valid:
            raise HTTPException(status_code=400, detail="Unknown curriculum.")

    # Enforce the plan's project cap (early access has none).
    cap = entitlements.project_cap(request.owner)
    if cap is not None and len(store.list_projects(request.owner)) >= cap:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your plan allows {cap} active projects. Upgrade for more, "
                "or delete one to make room."
            ),
        )

    project = store.create_project(
        owner=request.owner,
        title=request.title,
        question=request.question,
        curriculum_id=request.curriculum_id,
    )
    # The mentor speaks first — instantly, no model call (see mentor.py).
    kickoff = store.add_message(
        project["id"], "assistant", project_kickoff(project), mode="mentor"
    )
    return {
        "project": project,
        "messages": [kickoff],
        "bibliography": [],
        "insights": [],
        "hypotheses": [],
    }


@router.get("/janus/projects")
def list_projects(owner: str = Query(..., min_length=1, max_length=128)):
    return {"projects": store.list_projects(owner)}


@router.get("/janus/projects/{project_id}")
def get_project(
    project_id: int, owner: str = Query(..., min_length=1, max_length=128)
):
    project = _owned_project(project_id, owner)
    return {
        "project": project,
        "messages": store.get_messages(project_id),
        "bibliography": store.get_bibliography(project_id),
        "insights": store.get_insights(project_id),
        "hypotheses": store.get_hypotheses(project_id),
    }


@router.patch("/janus/projects/{project_id}")
def update_project(project_id: int, request: UpdateProjectRequest):
    _owned_project(project_id, request.owner)
    project = store.update_project(
        project_id,
        title=request.title,
        question=request.question,
        stage=request.stage,
    )
    return {"project": project}


@router.delete("/janus/projects/{project_id}")
def delete_project(
    project_id: int, owner: str = Query(..., min_length=1, max_length=128)
):
    _owned_project(project_id, owner)
    store.delete_project(project_id)
    return {"deleted": True}


@router.post("/janus/projects/{project_id}/chat")
def chat(project_id: int, request: ChatRequest):
    _owned_project(project_id, request.owner)
    if not os.getenv("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Janus needs the AI provider configured "
                "(OPENROUTER_API_KEY). The rest of Kairos works without it."
            ),
        )
    try:
        return run_turn(project_id, request.message, mode=request.mode)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mentor turn failed: {e}")


@router.post("/janus/projects/{project_id}/watch")
def toggle_watch(project_id: int, request: WatchRequest):
    """
    Turn proactive monitoring on/off for a project. Turning it on runs one
    instant check so the student gets immediate value rather than waiting for
    the next scheduled cycle.
    """
    _owned_project(project_id, request.owner)
    try:
        entitlements.require(request.owner, "proactive_monitoring")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=402, detail=str(e))

    project = store.update_project(project_id, watched=1 if request.watch else 0)
    result = {"project": project, "new_insight": False}
    if request.watch:
        try:
            check = proactive.check_now(project_id)
            result["new_insight"] = check["new_insight"]
            result["insights"] = store.get_insights(project_id)
        except Exception as e:
            # Monitoring is best-effort; never fail the toggle on a GEE hiccup.
            result["check_error"] = str(e)
    return result


@router.get("/janus/projects/{project_id}/pack", response_class=PlainTextResponse)
def download_pack(
    project_id: int, owner: str = Query(..., min_length=1, max_length=128)
):
    """The reproducibility pack as a downloadable Markdown document."""
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=402, detail=str(e))

    markdown = reproducibility.build_pack(project_id)
    filename = reproducibility.pack_filename(project)
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/janus/projects/{project_id}/notebook", response_class=PlainTextResponse)
def download_notebook(
    project_id: int, owner: str = Query(..., min_length=1, max_length=128)
):
    """A runnable Python Earth Engine script reproducing the project's analyses."""
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=402, detail=str(e))

    code = notebook.build_notebook(project_id)
    filename = notebook.notebook_filename(project)
    return PlainTextResponse(
        content=code,
        media_type="text/x-python; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/janus/projects/{project_id}/review")
def peer_review(
    project_id: int, owner: str = Query(..., min_length=1, max_length=128)
):
    """
    Generate a formal mock peer-review report of the whole project. Slow when
    the AI provider is configured (one deep-model call); instant deterministic
    checklist otherwise.
    """
    _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=402, detail=str(e))
    try:
        return {"markdown": review_report.build_review(project_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {e}")


@router.post("/janus/insights/{insight_id}/dismiss")
def dismiss_insight(insight_id: int):
    store.dismiss_insight(insight_id)
    return {"dismissed": True}
