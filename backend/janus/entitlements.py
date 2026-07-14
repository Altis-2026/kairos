"""
Janus subscription tiers and feature gating (docs/JANUS.md §5).

The tier -> features map is the single source of truth for what each plan
unlocks. Gating is real in the code today; billing is not yet wired, so the
default tier is deliberately generous ("early_access" unlocks everything)
while Janus is free during early access. When Stripe is connected, a
successful checkout calls store.set_tier(owner, tier) and nothing else here
changes: the gates already exist.

To make a feature paid later, move it out of the early_access set and into
the tier that should own it. Nothing else in the codebase needs editing.
"""

# Every gateable capability. `requires()` checks membership against a tier.
FEATURES = {
    "mentor_chat",          # the core conversational mentor
    "curricula",            # structured teaching tracks
    "run_analysis",         # live GEE analyses from the mentor
    "literature",           # OpenAlex literature search
    "grounded_knowledge",   # NASA/ESA-cited SAR primers
    "study_design",         # persisted study designs
    "deep_reasoning",       # Sonnet-tier design/review turns
    "reproducibility_pack", # exportable methods report (+ code + peer review)
    "proactive_monitoring", # autonomous new-pass watching
    "unlimited_projects",   # no cap on active projects
    "voice",                # voice mode (client-side today; premium TTS later)
    "autopilot",            # describe-it-and-Janus-runs-the-whole-investigation
    "priority_compute",     # jump the GEE queue (hook for later)
}

# Non-paying project cap for the metered tiers. early_access ignores it.
FREE_PROJECT_CAP = 3

TIERS = {
    # The current default: everyone, free, everything. This is what makes the
    # early-access launch feel unlimited while the gates quietly exist.
    "early_access": {
        "name": "Early Access",
        "price_usd_month": 0,
        "blurb": "Everything unlocked, free, while Janus is in early access.",
        "features": set(FEATURES),
        "project_cap": None,
    },
    "free": {
        "name": "Explorer",
        "price_usd_month": 0,
        "blurb": "Learn the craft and run real analyses, with a few projects.",
        "features": {
            "mentor_chat",
            "curricula",
            "run_analysis",
            "literature",
            "grounded_knowledge",
            "study_design",
        },
        "project_cap": FREE_PROJECT_CAP,
    },
    "student": {
        "name": "Student",
        "price_usd_month": 15,
        "blurb": "The full mentor for your own research. Voice, packs, monitoring.",
        "features": {
            "mentor_chat",
            "curricula",
            "run_analysis",
            "literature",
            "grounded_knowledge",
            "study_design",
            "deep_reasoning",
            "reproducibility_pack",
            "proactive_monitoring",
            "voice",
            "autopilot",
        },
        "project_cap": 10,
    },
    "researcher": {
        "name": "Researcher",
        "price_usd_month": 49,
        "blurb": "Unlimited projects, priority compute, every power tool.",
        "features": set(FEATURES),
        "project_cap": None,
    },
    "team": {
        "name": "Team / Classroom",
        "price_usd_month": 199,
        "blurb": "30 seats, shared projects, teacher dashboard.",
        "features": set(FEATURES),
        "project_cap": None,
    },
}

# What a brand-new owner gets before any billing exists.
DEFAULT_TIER = "early_access"


def resolve_tier(owner: str) -> str:
    """The owner's tier, from the plans table, defaulting to early access."""
    from janus import store

    return store.get_tier(owner) or DEFAULT_TIER


def entitlements(owner: str) -> dict:
    """Full entitlement snapshot for the frontend to gate its UI."""
    tier_id = resolve_tier(owner)
    tier = TIERS[tier_id]
    return {
        "tier": tier_id,
        "tier_name": tier["name"],
        "blurb": tier["blurb"],
        "features": sorted(tier["features"]),
        "project_cap": tier["project_cap"],
        # The upgrade ladder, so the UI can render a pricing prompt when a
        # gated feature is hit — without hardcoding prices in the frontend.
        "catalog": [
            {
                "id": tid,
                "name": t["name"],
                "price_usd_month": t["price_usd_month"],
                "blurb": t["blurb"],
            }
            for tid, t in TIERS.items()
            if tid not in ("early_access",)
        ],
    }


def has_feature(owner: str, feature: str) -> bool:
    return feature in TIERS[resolve_tier(owner)]["features"]


def project_cap(owner: str):
    return TIERS[resolve_tier(owner)]["project_cap"]


class FeatureLocked(Exception):
    """Raised when an owner's tier does not include a requested feature."""

    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(f"Your plan does not include '{feature}'.")


def require(owner: str, feature: str):
    """Gate a backend action. The API maps FeatureLocked to HTTP 402."""
    if not has_feature(owner, feature):
        raise FeatureLocked(feature)
