from fastapi import APIRouter, Depends, HTTPException

from ai.client import narrate_result, parse_natural_language
from api.analyze import run_analysis
from models.requests import QueryRequest
from ratelimit import limit_ai

router = APIRouter()


def _reply(understood, parsed, *, clarification=None, result=None, results=None, explanation=None):
    return {
        "understood": understood,
        "clarification": clarification,
        "parameters": parsed.model_dump() if parsed else None,
        "result": result,
        "results": results,
        "explanation": explanation,
    }


def _fallback_narration(result: dict) -> str:
    hs = result["headline_stat"]
    return (
        f"{result['display_name']} finished: {hs['label']} is {hs['value']} "
        f"{hs['unit']}, from Sentinel-1 data dated {result['data_date']}."
    )


@router.post("/query", dependencies=[Depends(limit_ai)])
def query(request: QueryRequest):
    history = [{"role": t.role, "content": t.content} for t in request.history] if request.history else None
    try:
        parsed = parse_natural_language(request.query, request.viewport_bbox, history, request.language)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"The language model did not answer in time ({type(e).__name__}). Try again in a moment.",
        )

    if not parsed.understood:
        return _reply(
            False,
            parsed,
            clarification=parsed.clarification or "Could you tell me what you want to analyze, and where?",
        )

    if request.parse_only:
        reply = _reply(True, parsed)
        reply["parse_only"] = True
        return reply

    if not (parsed.analysis_type and parsed.bbox and parsed.start_date and parsed.end_date):
        return _reply(
            False,
            parsed,
            clarification="I understood part of that, but I'm missing the place or "
            "the dates. Could you name a place and a time period?",
        )

    try:
        result = run_analysis(
            analysis_type=parsed.analysis_type,
            bbox=parsed.bbox,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
        )
    except ValueError as e:
        return _reply(True, parsed, explanation=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    results = [result]
    extra_notes = []
    for extra in parsed.extra_analyses or []:
        try:
            extra_result = run_analysis(
                analysis_type=extra.analysis_type,
                bbox=extra.bbox or parsed.bbox,
                start_date=extra.start_date or parsed.start_date,
                end_date=extra.end_date or parsed.end_date,
            )
        except Exception:
            continue
        results.append(extra_result)
        hs = extra_result["headline_stat"]
        extra_notes.append(f"{extra_result['display_name']}: {hs['label']} {hs['value']} {hs['unit']}")

    try:
        explanation = narrate_result(result, request.language)
    except Exception:
        explanation = _fallback_narration(result)
    if extra_notes:
        explanation += " Also added: " + "; ".join(extra_notes) + "."

    return _reply(True, parsed, result=result, results=results, explanation=explanation)
