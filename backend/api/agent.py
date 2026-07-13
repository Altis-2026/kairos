from fastapi import APIRouter, HTTPException

from models.requests import AgentPlanRequest, AgentReportRequest
from ai.client import fallback_mission_report, plan_mission, write_mission_report
from gee.registry import ANALYSIS_REGISTRY

router = APIRouter()


@router.post("/agent/plan")
def agent_plan(request: AgentPlanRequest):
    history = (
        [{"role": t.role, "content": t.content} for t in request.history]
        if request.history
        else None
    )
    try:
        plan = plan_mission(request.goal, request.viewport_bbox, history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mission planning failed: {e}")

    if not plan.understood:
        return {
            "understood": False,
            "plan_summary": None,
            "steps": None,
            "clarification": plan.clarification
            or "Could you say more about what the mission should find, and where?",
        }

    steps = [
        s.model_dump()
        for s in (plan.steps or [])
        if s.analysis_type in ANALYSIS_REGISTRY
    ][:4]
    if not steps:
        return {
            "understood": False,
            "plan_summary": None,
            "steps": None,
            "clarification": (
                "I could not turn that into concrete analyses. Could you name "
                "the region or event you want covered?"
            ),
        }

    return {
        "understood": True,
        "plan_summary": plan.plan_summary,
        "steps": steps,
        "clarification": None,
    }


@router.post("/agent/report")
def agent_report(request: AgentReportRequest):
    outcomes = [o.model_dump() for o in request.outcomes]
    try:
        report = write_mission_report(
            request.goal, request.plan_summary or "", outcomes
        )
    except Exception:
        report = fallback_mission_report(request.goal, outcomes)
    return {"report": report}
