import os

from janus import store

FEATURES = {
    "mentor_chat",
    "curricula",
    "run_analysis",
    "literature",
    "grounded_knowledge",
    "study_design",
    "deep_reasoning",
    "reproducibility_pack",
    "proactive_monitoring",
    "unlimited_projects",
    "voice",
    "autopilot",
    "priority_compute",
}

PROJECT_CAP = int(os.getenv("JANUS_PROJECT_CAP", "25"))

TIER = {
    "id": "open",
    "name": "Free",
    "blurb": "Every Janus feature, free for everyone.",
}


def entitlements(owner: str) -> dict:
    return {
        "tier": TIER["id"],
        "tier_name": TIER["name"],
        "blurb": TIER["blurb"],
        "features": sorted(FEATURES),
        "project_cap": PROJECT_CAP,
        "locked": False,
        "catalog": [],
        "skills": store.get_skills(owner),
        "unread_insights": store.unread_insight_count(owner),
    }


def has_feature(owner: str, feature: str) -> bool:
    return feature in FEATURES


def project_cap(owner: str) -> int:
    return PROJECT_CAP


class FeatureLocked(Exception):
    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(f"'{feature}' is not available.")


def require(owner: str, feature: str):
    if not has_feature(owner, feature):
        raise FeatureLocked(feature)
