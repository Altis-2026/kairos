"""
Janus curricula — structured teaching tracks the mentor walks a student
through, one conversational session at a time. Every session ends in a live
exercise the student actually runs on real Sentinel-1 data via the mentor's
run_analysis tool, so nothing stays theoretical.

The mentor reads these via its get_curriculum tool; it teaches FROM this
structure rather than inventing a syllabus, so two students on the same
track get the same course.
"""

CURRICULA = {
    "sar-fundamentals": {
        "id": "sar-fundamentals",
        "title": "SAR Fundamentals",
        "audience": "Anyone starting from zero. No physics background needed.",
        "outcome": (
            "You can read a radar image, explain what backscatter is, run a "
            "change detection honestly, and say how much to trust it."
        ),
        "sessions": [
            {
                "title": "How radar sees",
                "goals": [
                    "What a SAR satellite actually measures (backscatter, not photos)",
                    "Why microwaves pass through cloud and darkness",
                    "Bright vs dark: roughness, moisture, geometry",
                ],
                "exercise": {
                    "prompt": (
                        "Run a raw look at a place the student cares about, or "
                        "the Ganges delta [89.4, 22.6, 90.8, 23.8] over the last "
                        "month. Have the student predict which surfaces will be "
                        "bright and which dark BEFORE running, then check."
                    ),
                    "analysis_type": "flood_extent",
                },
            },
            {
                "title": "Polarization and scattering",
                "goals": [
                    "VV vs VH: what a second polarization adds",
                    "Surface, volume and double-bounce scattering",
                    "Why vegetation raises VH and cities blaze in VV",
                ],
                "exercise": {
                    "prompt": (
                        "Run crop monitoring over California's Central Valley "
                        "[-120.6, 36.2, -119.4, 37.2] for the current month and "
                        "have the student explain the RVI pattern in terms of "
                        "volume scattering."
                    ),
                    "analysis_type": "crop_monitoring",
                },
            },
            {
                "title": "Change detection and thresholds",
                "goals": [
                    "Baseline vs event window: the core of every detection",
                    "What a -3 dB threshold means physically",
                    "Reading the uncertainty range (threshold ensemble)",
                ],
                "exercise": {
                    "prompt": (
                        "Run a flood detection with a sensible baseline over a "
                        "monsoon region, then have the student interpret "
                        "area_low vs area_high and what the spread implies."
                    ),
                    "analysis_type": "flood_extent",
                },
            },
            {
                "title": "False positives and honest radar",
                "goals": [
                    "Wet farmland vs flood, calm wind vs oil slick",
                    "Speckle: why single pixels lie",
                    "How Kairos's optical fusion cross-checks a detection",
                ],
                "exercise": {
                    "prompt": (
                        "Run an oil spill detection in a low-traffic sea area "
                        "and have the student argue BOTH sides: why the "
                        "detection could be real, and what else could explain it."
                    ),
                    "analysis_type": "oil_spill",
                },
            },
            {
                "title": "Validation and confidence",
                "goals": [
                    "Ground truth: what it is and where to find it",
                    "IoU, precision, recall in plain language",
                    "Why a validated method beats a prettier map",
                ],
                "exercise": {
                    "prompt": (
                        "Run the bangladesh-monsoon-2017 ground-truth benchmark "
                        "and walk through every metric with the student until "
                        "they can explain precision vs recall in one sentence each."
                    ),
                    "analysis_type": "validation",
                },
            },
        ],
    },
    "question-to-study": {
        "id": "question-to-study",
        "title": "From Question to Study Design",
        "audience": (
            "Students and researchers who have a question about the Earth and "
            "want a design that would survive review."
        ),
        "outcome": (
            "A written, testable study design: hypothesis, area, windows, "
            "method, confounders and a validation plan, saved to the project."
        ),
        "sessions": [
            {
                "title": "Framing a testable question",
                "goals": [
                    "Vague interest to falsifiable hypothesis",
                    "Choosing the unit of analysis and the area of interest",
                    "What Sentinel-1 can and cannot answer",
                ],
                "exercise": {
                    "prompt": (
                        "Take the student's own interest and iterate until it is "
                        "a single falsifiable sentence with a defined AOI. Then "
                        "call update_study_design with the hypothesis and AOI."
                    ),
                    "analysis_type": None,
                },
            },
            {
                "title": "Choosing data and method",
                "goals": [
                    "Matching phenomena to analysis types and datasets",
                    "Revisit rates, resolution, and what they rule out",
                    "Checking data availability before committing",
                ],
                "exercise": {
                    "prompt": (
                        "Use search_datasets and preview_scene_availability for "
                        "the student's AOI, pick the method together, and save "
                        "it to the design."
                    ),
                    "analysis_type": None,
                },
            },
            {
                "title": "Baselines and confounders",
                "goals": [
                    "Seasonality, weather, agriculture: the usual suspects",
                    "Choosing baseline windows that do not cheat",
                    "Writing the confounder list before seeing results",
                ],
                "exercise": {
                    "prompt": (
                        "Run the planned analysis once, then have the student "
                        "list three non-target explanations for the signal and "
                        "save them as confounders in the design."
                    ),
                    "analysis_type": None,
                },
            },
            {
                "title": "Validation plan and writing up",
                "goals": [
                    "Picking ground truth for the claim being made",
                    "Reporting uncertainty instead of hiding it",
                    "A methods paragraph a reviewer could re-run",
                ],
                "exercise": {
                    "prompt": (
                        "Draft the validation plan into the design, then have "
                        "the student write their methods paragraph and review "
                        "it hard: overclaiming, missing caveats, causal leaps."
                    ),
                    "analysis_type": None,
                },
            },
        ],
    },
}


def curricula_summary() -> list:
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "audience": c["audience"],
            "outcome": c["outcome"],
            "sessions": [s["title"] for s in c["sessions"]],
        }
        for c in CURRICULA.values()
    ]


def get_curriculum(curriculum_id: str) -> dict:
    if curriculum_id not in CURRICULA:
        raise ValueError(
            f"Unknown curriculum '{curriculum_id}'. "
            f"Available: {list(CURRICULA.keys())}"
        )
    return CURRICULA[curriculum_id]
