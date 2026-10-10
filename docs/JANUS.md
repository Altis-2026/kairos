# Janus, the research mentor

Janus teaches people how to answer a question about the Earth the way a scientist
would, then works alongside them while they do it, using Kairos as the
instrument. It is a mentor rather than an answer machine: it asks about
reasoning, points out weak designs and reviews what the user produces.

Janus is free for everyone. Each visitor gets up to 25 active projects, and the
same per-IP limits as the rest of the API apply to its conversation turns.

## Modes

| Mode | What it does | Model |
|---|---|---|
| Mentor | Conversational teaching and guidance | Claude Haiku 4.5 |
| Study design | Turns an interest into a hypothesis, area, windows, analyses, confounders and a validation plan | Claude Sonnet 4.6 |
| Peer review | Adversarial review of the project's reasoning and results | Claude Sonnet 4.6 |
| Autopilot | Describe a goal and Janus runs the investigation, then reports | Claude Sonnet 4.6 |

## Tools

During a conversation the model can call real Kairos functions. Every tool call
and its result is stored with the project, so exports can only describe work that
actually happened.

| Tool | Purpose |
|---|---|
| `run_analysis`, `list_analysis_types`, `preview_scene_availability` | Run any registry analysis and check data availability |
| `compare_analyses`, `extract_time_series` | Compare places or windows and pull trend statistics |
| `run_ground_truth_validation`, `validate_against_my_data` | Score results against reference maps or the user's own data |
| `check_confounders`, `estimate_human_impact` | Test innocent explanations and estimate exposure |
| `search_literature`, `literature_review`, `save_reference`, `format_citations` | Search OpenAlex, summarize, and build a bibliography |
| `search_datasets`, `list_project_datasets` | Find datasets and use uploaded ones |
| `explain_concept`, `get_curriculum`, `record_skill` | Teach with cited primers and track what the learner has practiced |
| `log_hypothesis`, `update_hypothesis`, `update_study_design` | Keep the project's design current |

## Memory and monitoring

Projects live in SQLite (`backend/janus/store.py`): the question, stage, design,
hypotheses, datasets, bibliography, skills and every turn. A project can be put
on watch, and Janus then checks for new Sentinel-1 passes over the study area and
offers to re-run the analysis when one arrives.

## Exports

| Export | Endpoint |
|---|---|
| Reproducibility pack (Markdown) | `GET /janus/projects/{id}/pack` |
| LaTeX manuscript skeleton | `GET /janus/projects/{id}/latex` |
| Runnable Python notebook | `GET /janus/projects/{id}/notebook` |
| Policy brief | `GET /janus/projects/{id}/brief` |
| BibTeX and RIS bibliography | `GET /janus/projects/{id}/bibtex`, `/ris` |
| Peer-review report | `GET /janus/projects/{id}/review` |
| Figures (SVG) | `GET /janus/projects/{id}/figure/{kind}` |

## Honesty rules

Janus never invents a measurement, a citation or a dataset. Simulated results are
always labelled as simulations. Literature comes from real search results, and
grounded explanations cite NASA and ESA primers.
