"""
Janus mentor API.

  GET    /janus/status                  is the mentor available (API key set)?
  GET    /janus/curricula               teaching tracks
  POST   /janus/projects                create a project (+ mentor kickoff)
  GET    /janus/projects?owner=         list my projects
  GET    /janus/projects/{id}           project + messages + bibliography
  PATCH  /janus/projects/{id}           rename / edit question / stage
  DELETE /janus/projects/{id}           delete a project
  POST   /janus/projects/{id}/chat      one mentor turn (may run GEE tools)

Synchronous handlers throughout: mentor turns can invoke blocking GEE calls,
so FastAPI must run them in its threadpool (`def`, not `async def`).

Ownership is an honesty check, not security: `owner` is the Firebase uid or
an anonymous browser id. Real auth arrives with the paid tier.
"""

import os

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from janus import store
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


@router.get("/janus/curricula")
def get_curricula():
    return {"curricula": curricula_summary()}


@router.post("/janus/projects")
def create_project(request: CreateProjectRequest):
    if request.curriculum_id is not None:
        valid = {c["id"] for c in curricula_summary()}
        if request.curriculum_id not in valid:
            raise HTTPException(status_code=400, detail="Unknown curriculum.")
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
    return {"project": project, "messages": [kickoff], "bibliography": []}


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
