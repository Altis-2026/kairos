import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from janus import (
    entitlements,
    exports,
    figures,
    notebook,
    proactive,
    reproducibility,
    review_report,
    store,
)
from janus.curriculum import curricula_summary
from janus.mentor import project_kickoff, run_turn
from ratelimit import limit_ai

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
    mode: str = Field(default="mentor", pattern="^(mentor|design|review|autopilot)$")


class WatchRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    watch: bool


def _require_access(owner: str):
    try:
        entitlements.require(owner, "mentor_chat")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))


def _owned_project(project_id: int, owner: str) -> dict:
    try:
        project = store.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if project["owner"] != owner and not store.is_member(project_id, owner):
        raise HTTPException(status_code=403, detail="Not your project.")
    return project


def _strictly_owned(project_id: int, owner: str) -> dict:
    try:
        project = store.get_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if project["owner"] != owner:
        raise HTTPException(status_code=403, detail="Only the project owner can do that.")
    return project


@router.get("/janus/status")
def janus_status():
    from gee import earthdata

    return {
        "available": bool(os.getenv("OPENROUTER_API_KEY")),
        "earthdata": earthdata.status(),
    }


@router.get("/janus/entitlements")
def get_entitlements(owner: str = Query(..., min_length=1, max_length=128)):
    ent = entitlements.entitlements(owner)
    ent["unread_insights"] = store.unread_insight_count(owner)
    ent["skills"] = store.get_skills(owner)
    return ent


@router.get("/janus/curricula")
def get_curricula():
    return {"curricula": curricula_summary()}


@router.post("/janus/projects", dependencies=[Depends(limit_ai)])
def create_project(request: CreateProjectRequest):
    _require_access(request.owner)
    if request.curriculum_id is not None:
        valid = {c["id"] for c in curricula_summary()}
        if request.curriculum_id not in valid:
            raise HTTPException(status_code=400, detail="Unknown curriculum.")

    cap = entitlements.project_cap(request.owner)
    if cap is not None and len(store.list_projects(request.owner)) >= cap:
        raise HTTPException(
            status_code=403,
            detail=f"You can keep {cap} active projects. Delete one to make room.",
        )

    project = store.create_project(
        owner=request.owner,
        title=request.title,
        question=request.question,
        curriculum_id=request.curriculum_id,
    )
    kickoff = store.add_message(project["id"], "assistant", project_kickoff(project), mode="mentor")
    return {
        "project": project,
        "messages": [kickoff],
        "bibliography": [],
        "insights": [],
        "hypotheses": [],
    }


@router.get("/janus/projects")
def list_projects(owner: str = Query(..., min_length=1, max_length=128)):
    return {
        "projects": [p for p in store.list_projects(owner) if not (p.get("design") or {}).get("companion")]
    }


_COMPANION_KICKOFF = (
    "### Hey, I'm Janus\n"
    "This chat is always here, no project needed. Ask me anything:\n"
    '- how Kairos works ("how do I run a flood analysis?", "what\'s the '
    'lightning-bolt tool?")\n'
    "- any question about the Earth, satellites, or radar, or genuinely "
    "anything you're curious about\n"
    '- or just tell me what you want DONE ("check the Sundarbans for '
    "flooding this month\") and I'll run it for real.\n\n"
    "There's a mic button below if you'd rather talk, and the speaker "
    "toggle makes me talk back. When a conversation grows into real "
    "research, I'll suggest spinning it into its own project so nothing "
    "gets lost."
)


class CompanionRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)


@router.post("/janus/companion", dependencies=[Depends(limit_ai)])
def open_companion(request: CompanionRequest):
    for p in store.list_projects(request.owner):
        if (p.get("design") or {}).get("companion"):
            return {
                "project": p,
                "messages": store.get_messages(p["id"]),
                "bibliography": store.get_bibliography(p["id"]),
                "insights": store.get_insights(p["id"]),
                "hypotheses": store.get_hypotheses(p["id"]),
            }

    project = store.create_project(owner=request.owner, title="Ask Janus", question="")
    project = store.update_project(project["id"], design={"companion": True})
    kickoff = store.add_message(project["id"], "assistant", _COMPANION_KICKOFF, mode="mentor")
    return {
        "project": project,
        "messages": [kickoff],
        "bibliography": [],
        "insights": [],
        "hypotheses": [],
    }


@router.get("/janus/projects/{project_id}")
def get_project(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
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
def delete_project(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    _strictly_owned(project_id, owner)
    store.delete_project(project_id)
    return {"deleted": True}


class MemberRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    member: str = Field(min_length=1, max_length=128)


@router.post("/janus/projects/{project_id}/members")
def add_member(project_id: int, req: MemberRequest):
    _strictly_owned(project_id, req.owner)
    if req.member == req.owner:
        raise HTTPException(status_code=400, detail="You already own this project.")
    store.add_member(project_id, req.member)
    return {"members": store.list_members(project_id)}


@router.get("/janus/projects/{project_id}/members")
def project_members(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    _owned_project(project_id, owner)
    return {"members": store.list_members(project_id)}


@router.delete("/janus/projects/{project_id}/members/{member}")
def remove_member(
    project_id: int,
    member: str,
    owner: str = Query(..., min_length=1, max_length=128),
):
    _strictly_owned(project_id, owner)
    store.remove_member(project_id, member)
    return {"members": store.list_members(project_id)}


@router.get("/janus/shared")
def shared_projects(owner: str = Query(..., min_length=1, max_length=128)):
    return {"projects": store.shared_with(owner)}


@router.post("/janus/projects/{project_id}/chat", dependencies=[Depends(limit_ai)])
def chat(project_id: int, request: ChatRequest):
    _owned_project(project_id, request.owner)
    _require_access(request.owner)
    if not os.getenv("OPENROUTER_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Janus needs the AI provider configured "
                "(OPENROUTER_API_KEY). The rest of Kairos works without it."
            ),
        )
    if request.mode == "autopilot":
        try:
            entitlements.require(request.owner, "autopilot")
        except entitlements.FeatureLocked as e:
            raise HTTPException(status_code=403, detail=str(e))
    try:
        return run_turn(project_id, request.message, mode=request.mode)
    except HTTPException:
        raise
    except RuntimeError as e:
        # The key is present (checked above) but OpenRouter rejected it, or
        # some other configuration problem `_complete` already turned into a
        # plain message — a 503 and that message as-is, same as every other
        # AI entry point, rather than "Mentor turn failed: {e}" wrapping it
        # in a prefix that implies the mentor itself is what broke.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mentor turn failed: {e}")


@router.post("/janus/projects/{project_id}/watch")
def toggle_watch(project_id: int, request: WatchRequest):
    _owned_project(project_id, request.owner)
    try:
        entitlements.require(request.owner, "proactive_monitoring")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))

    project = store.update_project(project_id, watched=1 if request.watch else 0)
    result = {"project": project, "new_insight": False}
    if request.watch:
        try:
            check = proactive.check_now(project_id)
            result["new_insight"] = check["new_insight"]
            result["insights"] = store.get_insights(project_id)
        except Exception as e:
            result["check_error"] = str(e)
    return result


@router.get("/janus/projects/{project_id}/pack", response_class=PlainTextResponse)
def download_pack(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))

    markdown = reproducibility.build_pack(project_id)
    filename = reproducibility.pack_filename(project)
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/janus/projects/{project_id}/notebook", response_class=PlainTextResponse)
def download_notebook(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))

    code = notebook.build_notebook(project_id)
    filename = notebook.notebook_filename(project)
    return PlainTextResponse(
        content=code,
        media_type="text/x-python; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/janus/projects/{project_id}/figures")
def list_figures(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    _owned_project(project_id, owner)
    return {"figures": figures.available_figures(project_id)}


@router.get("/janus/projects/{project_id}/figure/{kind}")
def download_figure(
    project_id: int,
    kind: str,
    owner: str = Query(..., min_length=1, max_length=128),
    download: bool = Query(default=False),
):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))
    if kind not in figures.FIGURE_KINDS:
        raise HTTPException(status_code=404, detail=f"Unknown figure: {kind}")
    try:
        svg = figures.build_figure(project_id, kind)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{figures.figure_filename(project, kind)}"'
    return Response(content=svg, media_type="image/svg+xml", headers=headers)


def _attachment(content: str, filename: str, media_type: str) -> PlainTextResponse:
    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/janus/projects/{project_id}/latex", response_class=PlainTextResponse)
def download_latex(
    project_id: int,
    owner: str = Query(..., min_length=1, max_length=128),
    journal: str = Query(default="article", pattern="^(article|ieee)$"),
):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _attachment(
        exports.build_latex(project_id, journal=journal),
        exports.latex_filename(project),
        "application/x-tex; charset=utf-8",
    )


@router.get("/janus/projects/{project_id}/brief", response_class=PlainTextResponse)
def download_policy_brief(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _attachment(
        exports.build_policy_brief_html(project_id),
        exports.policy_brief_filename(project),
        "text/html; charset=utf-8",
    )


@router.get("/janus/projects/{project_id}/bibtex", response_class=PlainTextResponse)
def download_bibtex(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    return _attachment(
        exports.build_bibtex(project_id),
        exports.bibtex_filename(project),
        "application/x-bibtex; charset=utf-8",
    )


@router.get("/janus/projects/{project_id}/ris", response_class=PlainTextResponse)
def download_ris(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    return _attachment(
        exports.build_ris(project_id),
        exports.ris_filename(project),
        "application/x-research-info-systems; charset=utf-8",
    )


@router.get("/janus/projects/{project_id}/gdoc", response_class=PlainTextResponse)
def download_gdoc(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    project = _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _attachment(
        exports.build_gdoc_html(project_id),
        exports.gdoc_filename(project),
        "text/html; charset=utf-8",
    )


@router.get("/janus/projects/{project_id}/review")
def peer_review(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    _owned_project(project_id, owner)
    try:
        entitlements.require(owner, "reproducibility_pack")
    except entitlements.FeatureLocked as e:
        raise HTTPException(status_code=403, detail=str(e))
    try:
        return {"markdown": review_report.build_review(project_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {e}")


@router.get("/janus/projects/{project_id}/citations")
def citations(
    project_id: int,
    owner: str = Query(..., min_length=1, max_length=128),
    style: str = Query(default="apa", pattern="^(apa|agu|ieee)$"),
):
    _owned_project(project_id, owner)
    from janus.citations import format_bibliography

    return format_bibliography(project_id, style=style)


@router.post("/janus/insights/{insight_id}/dismiss")
def dismiss_insight(insight_id: int):
    store.dismiss_insight(insight_id)
    return {"dismissed": True}


class DatasetUpload(BaseModel):
    owner: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    geojson: dict | None = None
    csv: str | None = Field(default=None, max_length=1_000_000)


@router.post("/janus/projects/{project_id}/datasets")
def upload_dataset(project_id: int, req: DatasetUpload):
    from janus import datasets

    _owned_project(project_id, req.owner)
    if not req.geojson and not req.csv:
        raise HTTPException(status_code=400, detail="Provide either 'geojson' or 'csv'.")
    try:
        gj = req.geojson or datasets.csv_to_geojson(req.csv)
        saved = datasets.add_dataset(project_id, req.name, gj)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"dataset": saved}


@router.get("/janus/projects/{project_id}/datasets")
def project_datasets(project_id: int, owner: str = Query(..., min_length=1, max_length=128)):
    from janus import datasets

    _owned_project(project_id, owner)
    return {"datasets": datasets.list_datasets(project_id)}


@router.delete("/janus/projects/{project_id}/datasets/{dataset_id}")
def remove_dataset(
    project_id: int,
    dataset_id: int,
    owner: str = Query(..., min_length=1, max_length=128),
):
    from janus import datasets

    _owned_project(project_id, owner)
    datasets.delete_dataset(dataset_id, project_id)
    return {"deleted": True}
