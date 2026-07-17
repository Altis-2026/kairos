"""
Janus's SAR knowledge base — grounding, not fine-tuning.

A model can't be retrained inside this codebase, and parametric memory of
SAR physics is exactly the kind of thing that drifts subtly wrong. So instead
Janus is grounded: every concept below is a hand-written, technically
reviewed primer that cites the real public program that is authoritative for
it (NASA ARSET, the Alaska Satellite Facility, ESA/Copernicus, UN-SPIDER,
NASA/ISRO NISAR, NASA Earthdata, USGS). The mentor retrieves these via the
explain_concept tool and is instructed to answer core SAR physics FROM this
base rather than freehand, the same discipline search_literature enforces
for citations.

Every `resources` URL below is a real, stable top-level program page (not a
deep link liable to rot) so the mentor can point a student at primary
material instead of a fabricated citation.
"""

CONCEPTS = {
    "backscatter": {
        "title": "Radar backscatter",
        "explanation": (
            "A SAR satellite transmits microwave pulses and measures how much "
            "energy scatters back to the antenna. That returned energy, "
            "backscatter, depends on the target's roughness at the radar's "
            "wavelength, its dielectric (moisture) properties, and its "
            "geometry relative to the sensor. It is usually expressed in "
            "decibels (dB) as sigma-nought, a normalized radar cross-section. "
            "Smooth surfaces (calm water, pavement) act like mirrors and "
            "reflect the pulse away from the sensor, reading dark. Rough "
            "surfaces and complex structures scatter energy in all "
            "directions, including back to the sensor, reading bright."
        ),
        "resources": [
            {"name": "NASA ARSET: SAR fundamentals training", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
            {"name": "ASF: What is SAR?", "url": "https://asf.alaska.edu/information/sar-information/what-is-sar/"},
        ],
    },
    "polarization": {
        "title": "Polarization (VV, VH, HH, HV)",
        "explanation": (
            "SAR antennas transmit and receive in a chosen electric-field "
            "orientation, horizontal (H) or vertical (V). A two-letter code "
            "names transmit then receive: VV transmits and receives "
            "vertical, VH transmits vertical and receives horizontal (a "
            "cross-polarized channel). Cross-pol channels (VH, HV) are "
            "especially sensitive to volume scattering, energy bouncing "
            "around inside a 3D structure like a forest canopy or crop "
            "stand, which is why VH is used for deforestation and crop "
            "vigour. Co-pol channels (VV, HH) are more sensitive to surface "
            "and double-bounce scattering, better for water, ships and "
            "buildings. Sentinel-1 IW mode over land typically carries VV "
            "and VH together for exactly this complementary reason."
        ),
        "resources": [
            {"name": "ESA/Copernicus Sentinel Online", "url": "https://sentinels.copernicus.eu/"},
            {"name": "NASA ARSET: SAR fundamentals training", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
        ],
    },
    "scattering-mechanisms": {
        "title": "Surface, volume and double-bounce scattering",
        "explanation": (
            "Three canonical scattering mechanisms explain most of what a "
            "SAR image shows. Surface (single-bounce) scattering happens at "
            "one interface, bare soil, calm water, so the amount and "
            "roughness of that surface set the brightness. Volume "
            "scattering happens inside a 3D medium like vegetation, where "
            "the pulse bounces among leaves, branches and trunks before "
            "returning, which is why forests and mature crops look bright "
            "and speckly rather than mirror-dark. Double-bounce scattering "
            "happens at a right-angle interface, most classically the "
            "ground-to-building-wall corner in a city, and produces very "
            "bright, geometrically stable returns, which is why urban "
            "areas and ship hulls (deck-to-hull corners) are so bright in "
            "VV."
        ),
        "resources": [
            {"name": "NASA ARSET: SAR fundamentals training", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
            {"name": "UN-SPIDER Knowledge Portal", "url": "https://www.un-spider.org/"},
        ],
    },
    "speckle": {
        "title": "Speckle",
        "explanation": (
            "Because a SAR resolution cell contains many sub-wavelength "
            "scatterers whose individual returns interfere randomly, the "
            "measured brightness varies pixel to pixel even over a "
            "physically uniform surface, a salt-and-pepper noise pattern "
            "called speckle. It is not sensor noise you can simply average "
            "away in a single scene; it is fundamentally multiplicative. "
            "Two standard mitigations are temporal multi-looking (averaging "
            "several acquisitions of the same scene through time, which "
            "Kairos does for every baseline composite) and spatial "
            "filtering, a median or Lee filter over a small neighborhood "
            "(the despeckle step Kairos applies before thresholding). "
            "Reading a single unfiltered pixel as ground truth is a "
            "beginner's mistake; speckle is exactly why."
        ),
        "resources": [
            {"name": "ASF: What is SAR?", "url": "https://asf.alaska.edu/information/sar-information/what-is-sar/"},
            {"name": "UN-SPIDER Knowledge Portal", "url": "https://www.un-spider.org/"},
        ],
    },
    "insar-vs-amplitude": {
        "title": "InSAR phase vs. amplitude change detection",
        "explanation": (
            "SAR data carries two independent kinds of information per "
            "pixel: amplitude (how much energy returned, what Kairos's GRD-"
            "based detections use) and phase (the precise fraction of a "
            "wavelength the signal traveled, preserved only in SLC/complex "
            "data). Interferometric SAR (InSAR) compares the phase of two "
            "acquisitions of the same ground to measure millimetre-scale "
            "surface motion, the gold standard for subsidence, landslides "
            "and volcanic deformation. GRD, the product Kairos's registry "
            "runs on, discards phase, so any amplitude-based 'subsidence' "
            "detector (like Kairos's own) is a proxy for progressive ground "
            "change, not a displacement measurement, and should never be "
            "quoted in millimetres. A student who wants true InSAR needs "
            "SLC data and dedicated software (e.g. ESA SNAP, ISCE)."
        ),
        "resources": [
            {"name": "NASA/ISRO NISAR mission", "url": "https://nisar.jpl.nasa.gov/"},
            {"name": "ASF: What is SAR?", "url": "https://asf.alaska.edu/information/sar-information/what-is-sar/"},
        ],
    },
    "revisit-and-modes": {
        "title": "Revisit time, swath and acquisition modes",
        "explanation": (
            "A SAR satellite doesn't stare; it images a swath as it passes "
            "overhead, and how often it returns to the same ground (revisit "
            "time) trades off against swath width and resolution. "
            "Sentinel-1's Interferometric Wide (IW) mode, the workhorse over "
            "land and coasts, covers a 250 km swath at ~10 m resolution "
            "roughly every 12 days per satellite. Extra Wide (EW) mode "
            "trades resolution for a 400 km swath, used almost exclusively "
            "over polar sea ice where coverage matters more than detail. "
            "Revisit time is the hard ceiling on how fast a change can be "
            "detected: a flood that rises and recedes inside one revisit "
            "gap is invisible to Sentinel-1 alone, a real limitation worth "
            "stating plainly in any study design."
        ),
        "resources": [
            {"name": "ESA/Copernicus Sentinel Online", "url": "https://sentinels.copernicus.eu/"},
            {"name": "NASA Earthdata", "url": "https://www.earthdata.nasa.gov/"},
        ],
    },
    "change-detection-design": {
        "title": "Designing a defensible change detection",
        "explanation": (
            "A credible SAR change detection needs, at minimum: a baseline "
            "window chosen BEFORE looking at results (never cherry-picked "
            "after seeing the answer, which is baseline leakage); a "
            "threshold justified by the physics of the mechanism, not "
            "tuned to produce a nicer-looking map; an explicit list of "
            "confounders considered and ruled out (rainfall before a "
            "'flood', wind before an 'oil spill', harvest before "
            "'deforestation'); and a stated validation approach, even an "
            "approximate one, against an independent reference. Kairos's "
            "own detectors follow this pattern (fixed dB thresholds, a "
            "documented baseline, a ground-truth validation suite); a "
            "student's own study should too."
        ),
        "resources": [
            {"name": "UN-SPIDER Knowledge Portal", "url": "https://www.un-spider.org/"},
            {"name": "NASA ARSET: SAR fundamentals training", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
        ],
    },
    "optical-vs-radar": {
        "title": "Why radar where optical fails",
        "explanation": (
            "Optical sensors (Landsat, Sentinel-2, MODIS) measure reflected "
            "sunlight, so they are blind through cloud and at night, "
            "precisely the conditions under which floods, active fires and "
            "storms occur. SAR is active (it carries its own illumination) "
            "and microwave (cloud is largely transparent at C-band, "
            "Sentinel-1's wavelength), so it images day, night, and through "
            "weather. The tradeoff: optical bands map composition directly "
            "(a red pixel is red), while radar backscatter must be "
            "interpreted through scattering physics, which is why radar "
            "literacy is a real, teachable skill rather than something "
            "read off at a glance."
        ),
        "resources": [
            {"name": "NASA Earthdata", "url": "https://www.earthdata.nasa.gov/"},
            {"name": "USGS Landsat Missions", "url": "https://www.usgs.gov/landsat-missions"},
        ],
    },
    "geometric-artifacts": {
        "title": "Layover, foreshortening and radar shadow",
        "explanation": (
            "SAR measures distance, not angle, so terrain distorts the image "
            "in ways optical users don't expect. Foreshortening: slopes "
            "facing the sensor are compressed and read unnaturally bright — "
            "a mountainside can shrink to a bright sliver. Layover: when a "
            "slope is steeper than the radar's incidence angle, the mountain "
            "TOP is closer to the satellite than its base, so the peak is "
            "imaged on the wrong side — the mountain folds over itself. "
            "Shadow: behind steep terrain the radar simply cannot see, and "
            "those pixels contain no data at all (not 'dark ground' — "
            "nothing). Any detection inside layover or shadow zones is "
            "unreliable, which is why mountainous AOIs deserve extra "
            "scepticism and why ascending vs descending orbit passes see "
            "different sides of the same ridge."
        ),
        "resources": [
            {"name": "ASF: SAR image distortions", "url": "https://asf.alaska.edu/information/sar-information/what-is-sar/"},
            {"name": "NASA ARSET: SAR fundamentals training", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
        ],
    },
    "incidence-angle": {
        "title": "Incidence angle",
        "explanation": (
            "The angle between the radar beam and the vertical at the ground "
            "— roughly 30-46 degrees across a Sentinel-1 IW swath. The same "
            "field can read several dB brighter at the near edge of the "
            "swath than the far edge, purely from geometry. This matters "
            "whenever you compare scenes: two passes with different "
            "geometries over the same spot are not directly comparable "
            "pixel-for-pixel. Kairos's change detections mitigate this by "
            "compositing multiple scenes per window, but a careful study "
            "notes it, and a reviewer WILL ask. Filtering to a single "
            "relative orbit is the rigorous fix when precision matters."
        ),
        "resources": [
            {"name": "ESA Sentinel-1 acquisition modes", "url": "https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes"},
        ],
    },
    "coherence-vs-amplitude": {
        "title": "Coherence vs amplitude (and what Kairos can/can't do)",
        "explanation": (
            "Amplitude is how much energy comes back; coherence is whether "
            "the PHASE relationship between two passes stays stable. "
            "Coherence-based change detection is exquisitely sensitive — a "
            "field being ploughed or a building collapsing destroys phase "
            "stability before the amplitude changes much. But coherence "
            "requires SLC (single-look complex) products that keep the phase, "
            "and interferometric processing. The free Sentinel-1 archive in "
            "Earth Engine is GRD — amplitude only, phase discarded — so "
            "Kairos's detections are amplitude-based, and honest about it. "
            "True coherence/InSAR (millimetre deformation, earthquake "
            "damage proxies) needs SLC processing infrastructure — it is on "
            "the Kairos roadmap as exactly that."
        ),
        "resources": [
            {"name": "ASF: InSAR introduction", "url": "https://asf.alaska.edu/information/sar-information/what-is-insar/"},
            {"name": "ESA InSAR principles", "url": "https://www.esa.int/Applications/Observing_the_Earth/"},
        ],
    },
    "l-band-penetration": {
        "title": "L-band penetration: seeing under sand and canopy",
        "explanation": (
            "Penetration scales with wavelength. C-band (~5.5 cm, Sentinel-1) "
            "interacts with leaves and the upper canopy; L-band (~24 cm, "
            "ALOS PALSAR, NISAR) passes through foliage to trunks and ground, "
            "and in hyper-arid sand can reach metres below the surface — "
            "SIR-A famously imaged buried paleochannels under the Sahara in "
            "1982, and L-band archaeology has mapped features invisible on "
            "the ground since. The catch: penetration in soil requires "
            "EXTREMELY dry conditions (moisture kills it), and 'seeing "
            "under canopy' means the return mixes ground and trunk signals, "
            "not that you get a clean picture of the floor. Kairos's "
            "Archaeology Mode and biomass analysis both ride on PALSAR "
            "L-band mosaics for exactly these reasons."
        ),
        "resources": [
            {"name": "JAXA ALOS PALSAR", "url": "https://www.eorc.jaxa.jp/ALOS/en/dataset/palsar_e.htm"},
            {"name": "NASA NISAR mission", "url": "https://nisar.jpl.nasa.gov/"},
        ],
    },
    "minimum-mapping-unit": {
        "title": "Minimum mapping unit and mixed pixels",
        "explanation": (
            "A 10 m Sentinel-1 pixel covers 100 m². A detection smaller than "
            "a few pixels is indistinguishable from speckle, which is why "
            "honest SAR mapping states a minimum mapping unit — the smallest "
            "feature the method can reliably claim — typically several times "
            "the pixel area after speckle filtering. Mixed pixels (half "
            "water, half field) return intermediate values that threshold "
            "methods assign arbitrarily, so area estimates carry an inherent "
            "boundary uncertainty proportional to the perimeter. Reviewers "
            "ask about both; Kairos's uncertainty ranges (threshold "
            "ensembles) are one honest answer, and quoting area to the "
            "nearest 0.01 km² from 10 m pixels is the classic mistake."
        ),
        "resources": [
            {"name": "NASA ARSET: SAR for land applications", "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset"},
        ],
    },
}

RESOURCE_DIRECTORY = [
    {
        "name": "NASA ARSET (Applied Remote Sensing Training)",
        "url": "https://appliedsciences.nasa.gov/what-we-do/capacity-building/arset",
        "good_for": "Free structured courses on SAR and optical remote sensing, aimed at practitioners.",
    },
    {
        "name": "Alaska Satellite Facility (ASF) DAAC",
        "url": "https://asf.alaska.edu/",
        "good_for": "NASA's SAR data archive and the clearest public SAR primers and tutorials.",
    },
    {
        "name": "ESA / Copernicus Sentinel Online",
        "url": "https://sentinels.copernicus.eu/",
        "good_for": "Official Sentinel-1/2 mission documentation, product guides, and technical specs.",
    },
    {
        "name": "UN-SPIDER Knowledge Portal",
        "url": "https://www.un-spider.org/",
        "good_for": "Applied recommended practices for disaster response with SAR (floods, damage).",
    },
    {
        "name": "NASA/ISRO NISAR mission",
        "url": "https://nisar.jpl.nasa.gov/",
        "good_for": "The reference mission for InSAR deformation mapping; explains phase-based SAR well.",
    },
    {
        "name": "NASA Earthdata",
        "url": "https://www.earthdata.nasa.gov/",
        "good_for": "The umbrella catalog and documentation for essentially all NASA EO data.",
    },
    {
        "name": "USGS Landsat Missions",
        "url": "https://www.usgs.gov/landsat-missions",
        "good_for": "The long-running optical archive Kairos's optical fusion draws on.",
    },
]


def list_concepts() -> list:
    return [{"id": k, "title": v["title"]} for k, v in CONCEPTS.items()]


def explain_concept(concept_id: str) -> dict:
    if concept_id not in CONCEPTS:
        return {
            "error": f"No primer for '{concept_id}'.",
            "available": list_concepts(),
        }
    c = CONCEPTS[concept_id]
    return {"title": c["title"], "explanation": c["explanation"], "resources": c["resources"]}


def search_concepts(query: str) -> list:
    terms = [t for t in query.lower().split() if len(t) > 2]
    scored = []
    for cid, c in CONCEPTS.items():
        haystack = (c["title"] + " " + c["explanation"]).lower()
        score = sum(haystack.count(t) for t in terms)
        if score > 0:
            scored.append((score, cid))
    scored.sort(key=lambda pair: -pair[0])
    return [explain_concept(cid) | {"id": cid} for _, cid in scored[:3]]
