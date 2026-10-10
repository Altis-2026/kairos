from fastapi import APIRouter, HTTPException

import featured

router = APIRouter()


@router.get("/featured")
def list_featured():
    return {"stories": featured.STORIES, "status": featured.status()}


@router.post("/featured/{story_id}")
def run_featured(story_id: str):
    if story_id not in featured.BY_ID:
        raise HTTPException(status_code=404, detail="Unknown featured story.")
    try:
        return featured.run_story(story_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
