from fastapi import APIRouter, HTTPException
from models.requests import QueryRequest
from api.analyze import run_analysis
from ai.client import parse_natural_language, narrate_result

router = APIRouter()


@router.post("/query")
def query(request: QueryRequest):
    history = (
        [{"role": t.role, "content": t.content} for t in request.history]
        if request.history
        else None
    )
    try:
        parsed = parse_natural_language(
            request.query, request.viewport_bbox, history
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query parsing failed: {e}")

    if not parsed.understood:
        return {
            "understood": False,
            "clarification": parsed.clarification
            or "Could you tell me more about what you want to analyze, and where?",
            "parameters": parsed.model_dump(),
            "result": None,
            "explanation": None,
        }

    if not (parsed.analysis_type and parsed.bbox and parsed.start_date and parsed.end_date):
        return {
            "understood": False,
            "clarification": "I understood part of that, but I'm missing the "
            "location or dates. Could you name a place and a time period?",
            "parameters": parsed.model_dump(),
            "result": None,
            "explanation": None,
        }

    try:
        result = run_analysis(
            analysis_type=parsed.analysis_type,
            bbox=parsed.bbox,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
        )
    except ValueError as e:
        return {
            "understood": True,
            "clarification": None,
            "parameters": parsed.model_dump(),
            "result": None,
            "results": None,
            "explanation": str(e),
        }
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
            results.append(extra_result)
            hs = extra_result["headline_stat"]
            extra_notes.append(
                f"{extra_result['display_name']}: {hs['label']} "
                f"{hs['value']} {hs['unit']}"
            )
        except Exception:
            continue

    try:
        explanation = narrate_result(result)
    except Exception:
        hs = result["headline_stat"]
        explanation = (
            f"{result['display_name']} complete: {hs['label']} = "
            f"{hs['value']} {hs['unit']} based on Sentinel-1 data "
            f"from {result['data_date']}."
        )
    if extra_notes:
        explanation += " Also added: " + "; ".join(extra_notes) + "."

    return {
        "understood": True,
        "clarification": None,
        "parameters": parsed.model_dump(),
        "result": result,
        "results": results,
        "explanation": explanation,
    }
