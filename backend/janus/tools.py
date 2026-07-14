"""
Janus's hands: the tools the mentor can call while it works with a student.

Each tool returns two things:
  - a compact `payload` that goes back to the model (kept small on purpose;
    tile URLs and rasters never ride through the prompt), and
  - an `event` for the frontend: a human-readable chip in the conversation,
    carrying the full analysis result when there is one so the UI can put it
    straight onto the globe.

This is the moat in code form (docs/JANUS.md §8): a generic chatbot can talk
about a flood; Janus runs the flood analysis mid-sentence and reads the
actual numbers back to the student.
"""

import json

from janus import catalog, curriculum, knowledge, literature, store

# OpenAI function-calling schemas, served to OpenRouter with every turn.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_analysis_types",
            "description": (
                "List every analysis Kairos can run (id, name, what it "
                "detects, its data sources). Call before recommending an "
                "analysis if unsure of the exact id."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": (
                "Run a real Kairos satellite analysis. Slow (10-60 s) and "
                "the result appears on the student's globe, so confirm the "
                "parameters with the student before calling. Dates are "
                "YYYY-MM-DD; bbox is [min_lon, min_lat, max_lon, max_lat] "
                "and should usually span less than ~2 degrees."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["analysis_type", "bbox", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preview_scene_availability",
            "description": (
                "Check how many Sentinel-1 scenes cover a bbox and date range "
                "BEFORE designing a study around it. Fast and free."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["bbox", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_literature",
            "description": (
                "Search real scholarly literature (OpenAlex). The ONLY "
                "permitted source of citations: never mention a paper that "
                "this tool did not return in this project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "year_from": {
                        "type": "integer",
                        "description": "Only papers from this year onward",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_reference",
            "description": (
                "Save a paper (found via search_literature) into the "
                "project's annotated bibliography, with a note on why it "
                "matters to this study."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "authors": {"type": "string"},
                    "year": {"type": "integer"},
                    "venue": {"type": "string"},
                    "url": {"type": "string", "description": "DOI URL preferred"},
                    "note": {
                        "type": "string",
                        "description": "One sentence: why this paper matters here",
                    },
                },
                "required": ["title", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_datasets",
            "description": (
                "Search the curated Earth-observation dataset index (all "
                "free, all on Earth Engine). Returns what each dataset "
                "measures, its cadence and, crucially, its limits."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_concept",
            "description": (
                "Look up a grounded SAR/remote-sensing physics primer "
                "(backscatter, polarization, scattering mechanisms, speckle, "
                "InSAR vs amplitude, revisit/modes, change-detection design, "
                "optical vs radar), each citing real NASA/ESA/UN-SPIDER "
                "resources. Use this to teach core physics accurately "
                "rather than explaining from memory, especially in "
                "sar-fundamentals sessions. Omit concept_id to search by "
                "free text instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "concept_id": {
                        "type": "string",
                        "enum": [
                            "backscatter",
                            "polarization",
                            "scattering-mechanisms",
                            "speckle",
                            "insar-vs-amplitude",
                            "revisit-and-modes",
                            "change-detection-design",
                            "optical-vs-radar",
                        ],
                    },
                    "query": {
                        "type": "string",
                        "description": "Free-text search if concept_id is unknown",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_ground_truth_validation",
            "description": (
                "Run one of Kairos's ground-truth benchmarks: the production "
                "detector vs an independent reference map, returning live "
                "IoU/precision/recall/F1. Very slow (30-90 s). Benchmark ids: "
                "bangladesh-monsoon-2017, camp-fire-2018, "
                "rondonia-clearing-2020."
            ),
            "parameters": {
                "type": "object",
                "properties": {"benchmark_id": {"type": "string"}},
                "required": ["benchmark_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_human_impact",
            "description": (
                "Estimate people and built-up area inside a detection "
                "footprint (GHSL). Runs the analysis again, so slow; use for "
                "a detection already discussed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["analysis_type", "bbox", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_study_design",
            "description": (
                "Save agreed elements of the study design to the project. "
                "Call whenever the student settles a design element; pass "
                "only the fields that changed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string"},
                    "place": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "analysis_types": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "confounders": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "validation_plan": {"type": "string"},
                    "stage": {
                        "type": "string",
                        "enum": [
                            "exploring",
                            "designing",
                            "analyzing",
                            "validating",
                            "writing",
                        ],
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_confounders",
            "description": (
                "Actually test a detection's false-positive modes. Pulls real "
                "rainfall (CHIRPS), wind (ERA5) and land cover (WorldCover) for "
                "the AOI and dates and judges whether a confounder plausibly "
                "explains the signal (e.g. did rain wet the ground before a "
                "'flood', was wind too low so calm sea mimics an 'oil slick', is "
                "it cropland whose harvest mimics 'clearing'). Run this whenever "
                "you interpret a detection the student cares about. Slow (~20 s)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                },
                "required": ["analysis_type", "bbox", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_hypothesis",
            "description": (
                "Record a hypothesis in the project's research log once the "
                "student commits to one. Keep it a single falsifiable statement."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "evidence": {
                        "type": "string",
                        "description": "Optional initial note on evidence so far",
                    },
                },
                "required": ["statement"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_hypothesis",
            "description": (
                "Update a logged hypothesis after evidence comes in: set its "
                "status and add a note on what supported or undercut it. Use the "
                "hypothesis id from the research log in project context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hypothesis_id": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "enum": ["open", "supported", "refuted", "inconclusive"],
                    },
                    "evidence": {"type": "string"},
                },
                "required": ["hypothesis_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_skill",
            "description": (
                "Note a research skill the student has just demonstrated or is "
                "learning, so you can teach adaptively across all their "
                "projects. Use sparingly, for real milestones (e.g. 'reading a "
                "change-detection result', 'choosing a non-leaky baseline')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "level": {
                        "type": "string",
                        "enum": ["learning", "practiced", "confident"],
                    },
                    "note": {"type": "string"},
                },
                "required": ["skill", "level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_curriculum",
            "description": (
                "Fetch a teaching curriculum (or the list of all curricula "
                "if no id given). Teach FROM this structure; do not invent "
                "a syllabus."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "curriculum_id": {
                        "type": "string",
                        "enum": ["sar-fundamentals", "question-to-study"],
                    }
                },
            },
        },
    },
]


def _slim_result(result: dict) -> dict:
    """Analysis result cut down for the prompt: scalars only, no tile URLs."""
    slim = {
        "analysis_type": result.get("analysis_type"),
        "display_name": result.get("display_name"),
        "data_date": result.get("data_date"),
        "confidence": result.get("confidence"),
        "headline_stat": result.get("headline_stat"),
    }
    stats = result.get("stats") or {}
    slim["stats"] = {
        k: v for k, v in stats.items() if isinstance(v, (int, float, str, bool))
    }
    return slim


def execute_tool(name: str, args: dict, project_id: int) -> tuple:
    """
    Run one tool call. Returns (payload_for_model, event_for_frontend).
    Errors come back as payloads, not exceptions — the mentor should read
    the failure and adapt, not crash the turn.
    """
    try:
        if name == "list_analysis_types":
            from gee.registry import registry_as_json

            types = [
                {
                    "id": t["id"],
                    "name": t["display_name"],
                    "description": t["description"],
                    "data_sources": t["data_sources"],
                }
                for t in registry_as_json()
            ]
            return {"analysis_types": types}, {
                "tool": name,
                "label": f"Listed {len(types)} analysis types",
                "status": "ok",
            }

        if name == "run_analysis":
            from api.analyze import run_analysis

            result = run_analysis(
                analysis_type=args["analysis_type"],
                bbox=args["bbox"],
                start_date=args["start_date"],
                end_date=args["end_date"],
            )
            # Remember this run so proactive monitoring knows what to watch
            # over this AOI and from which imagery date onward.
            store.record_last_run(
                project_id,
                {
                    "analysis_type": result.get("analysis_type"),
                    "display_name": result.get("display_name"),
                    "bbox": result.get("bbox"),
                    "start_date": result.get("start_date"),
                    "end_date": result.get("end_date"),
                    "data_date": result.get("data_date"),
                },
            )
            hs = result.get("headline_stat") or {}
            return _slim_result(result), {
                "tool": name,
                "label": (
                    f"Ran {result.get('display_name')}: "
                    f"{hs.get('label')} = {hs.get('value')} {hs.get('unit')}"
                ),
                "status": "ok",
                # Full payload so the UI can drop the result on the globe.
                "result": result,
            }

        if name == "preview_scene_availability":
            from gee import common

            geometry = common.bbox_geometry(args["bbox"])
            coll = common.s1_collection(geometry).filterDate(
                args["start_date"], args["end_date"]
            )
            count = coll.size().getInfo()
            payload = {"scene_count": count}
            if count > 0:
                payload["latest_scene"] = common.latest_image_date(coll)
            return payload, {
                "tool": name,
                "label": f"Checked coverage: {count} Sentinel-1 scenes",
                "status": "ok",
            }

        if name == "search_literature":
            papers = literature.search_literature(
                args["query"], year_from=args.get("year_from")
            )
            if not papers:
                return (
                    {
                        "papers": [],
                        "note": (
                            "Literature index unreachable or no matches. Say "
                            "so plainly; do NOT cite from memory."
                        ),
                    },
                    {
                        "tool": name,
                        "label": f"Literature search: no results for “{args['query']}”",
                        "status": "empty",
                    },
                )
            return {"papers": papers}, {
                "tool": name,
                "label": f"Found {len(papers)} papers for “{args['query']}”",
                "status": "ok",
                "papers": papers,
            }

        if name == "save_reference":
            added = store.add_reference(
                project_id,
                title=args["title"],
                authors=args.get("authors"),
                year=args.get("year"),
                venue=args.get("venue"),
                url=args.get("url"),
                note=args.get("note"),
            )
            return {"saved": added, "already_in_bibliography": not added}, {
                "tool": name,
                "label": f"Saved to bibliography: {args['title'][:70]}",
                "status": "ok",
            }

        if name == "search_datasets":
            results = catalog.search_datasets(args["query"])
            return {"datasets": results}, {
                "tool": name,
                "label": f"Dataset scout: {len(results)} matches",
                "status": "ok",
                "datasets": results,
            }

        if name == "explain_concept":
            cid = args.get("concept_id")
            if cid:
                primer = knowledge.explain_concept(cid)
                if "error" in primer:
                    return primer, {
                        "tool": name,
                        "label": f"No primer for '{cid}'",
                        "status": "empty",
                    }
                return primer, {
                    "tool": name,
                    "label": f"Grounded explainer: {primer['title']}",
                    "status": "ok",
                    "concept": primer,
                }
            query = args.get("query", "")
            matches = knowledge.search_concepts(query) if query else []
            if not matches:
                return {"concepts": [], "available": knowledge.list_concepts()}, {
                    "tool": name,
                    "label": f"No grounded primer matched “{query}”",
                    "status": "empty",
                }
            return {"concepts": matches}, {
                "tool": name,
                "label": f"Grounded explainer: {matches[0]['title']}",
                "status": "ok",
                "concept": matches[0],
            }

        if name == "run_ground_truth_validation":
            from gee.validation import run_benchmark

            report = run_benchmark(args["benchmark_id"])
            payload = {
                "benchmark": report["benchmark"]["region"],
                "metrics": report["metrics"],
                "caveats": report["caveats"],
            }
            m = report["metrics"]
            return payload, {
                "tool": name,
                "label": (
                    f"Validated vs ground truth: IoU {m.get('iou')}, "
                    f"precision {m.get('precision')}, recall {m.get('recall')}"
                ),
                "status": "ok",
                "validation": report,
            }

        if name == "estimate_human_impact":
            from gee.impact import assess_impact

            result = assess_impact(
                analysis_type=args["analysis_type"],
                bbox=args["bbox"],
                start_date=args["start_date"],
                end_date=args["end_date"],
            )
            return result, {
                "tool": name,
                "label": (
                    f"Impact: ~{result['population_affected']:,} people, "
                    f"{result['built_up_km2']} km² built-up in footprint"
                ),
                "status": "ok",
            }

        if name == "update_study_design":
            stage = args.pop("stage", None)
            project = store.update_project(
                project_id, stage=stage, design=args
            )
            return {"design": project["design"], "stage": project["stage"]}, {
                "tool": name,
                "label": "Study design updated",
                "status": "ok",
                "design": project["design"],
            }

        if name == "check_confounders":
            from gee.confounders import analyze_confounders

            report = analyze_confounders(
                analysis_type=args["analysis_type"],
                bbox=args["bbox"],
                start_date=args["start_date"],
                end_date=args["end_date"],
            )
            return report, {
                "tool": name,
                "label": (
                    f"Confounder check: {report['overall_concern']} concern of "
                    "a false-positive driver"
                ),
                "status": "ok",
                "confounders": report,
            }

        if name == "log_hypothesis":
            hyp = store.add_hypothesis(
                project_id, args["statement"], evidence=args.get("evidence")
            )
            return {"hypothesis": hyp}, {
                "tool": name,
                "label": f"Logged hypothesis: {args['statement'][:70]}",
                "status": "ok",
                "hypothesis": hyp,
            }

        if name == "update_hypothesis":
            hyp = store.update_hypothesis(
                args["hypothesis_id"],
                status=args.get("status"),
                evidence=args.get("evidence"),
            )
            return {"hypothesis": hyp}, {
                "tool": name,
                "label": f"Hypothesis now: {hyp['status']}",
                "status": "ok",
                "hypothesis": hyp,
            }

        if name == "record_skill":
            owner = store.get_project(project_id)["owner"]
            saved = store.record_skill(
                owner, args["skill"], args["level"], note=args.get("note")
            )
            return {"skill": saved}, {
                "tool": name,
                "label": f"Skill noted: {args['skill']} ({args['level']})",
                "status": "ok",
            }

        if name == "get_curriculum":
            cid = args.get("curriculum_id")
            if cid:
                return {"curriculum": curriculum.get_curriculum(cid)}, {
                    "tool": name,
                    "label": f"Opened curriculum: {cid}",
                    "status": "ok",
                }
            return {"curricula": curriculum.curricula_summary()}, {
                "tool": name,
                "label": "Listed curricula",
                "status": "ok",
            }

        return {"error": f"Unknown tool '{name}'."}, {
            "tool": name,
            "label": f"Unknown tool {name}",
            "status": "error",
        }

    except ValueError as e:
        # User-facing tool failures (no data, bad params): mentor adapts.
        return {"error": str(e)}, {
            "tool": name,
            "label": f"{name} failed: {str(e)[:90]}",
            "status": "error",
        }
    except Exception as e:
        return {"error": f"Tool failed: {e}"}, {
            "tool": name,
            "label": f"{name} failed",
            "status": "error",
        }


def parse_tool_args(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
