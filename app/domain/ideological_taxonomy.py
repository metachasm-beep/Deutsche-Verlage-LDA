"""
Candidate 2: Ideological Regime & Imprint Taxonomy Module.

Deepens all domain rules governing Ideological Regimes (RQ1, RQ2, RQ3), seed lexicons,
morphological stem prefixes, and Imprint attribution behind a single authoritative interface.
"""
from __future__ import annotations

import config

REGIME_TRADITIONAL = "Traditional / Ecclesiastical"
REGIME_NEOLIBERAL = "Neoliberal / Self-Optimization"
REGIME_CRITICAL = "Critical / Secular-Humanist"

CANONICAL_REGIMES: tuple[str, str, str] = (
    REGIME_TRADITIONAL,
    REGIME_NEOLIBERAL,
    REGIME_CRITICAL,
)

LEGACY_REGIME_ALIASES: dict[str, str] = {
    "Traditional / Theological": REGIME_TRADITIONAL,
    "Traditional / Ecclesiastical": REGIME_TRADITIONAL,
    "Traditional": REGIME_TRADITIONAL,
    "Neoliberal / Self-Help": REGIME_NEOLIBERAL,
    "Neoliberal / Self-Optimization": REGIME_NEOLIBERAL,
    "Neoliberal": REGIME_NEOLIBERAL,
    "Critical / Secular-Academic": REGIME_CRITICAL,
    "Critical / Secular-Humanist": REGIME_CRITICAL,
    "Critical": REGIME_CRITICAL,
}

ARCHETYPE_STEM_PREFIXES: dict[str, tuple[str, ...]] = {
    REGIME_TRADITIONAL: (
        "kirchen", "kirchlich", "gottes", "christus", "christlich", "evangeli", "kathol",
        "seelsorg", "gemeinde", "dogmat", "liturg", "sakrament", "theolog", "pfarr",
        "bischof", "ökumen", "frömmig", "predig", "heilig", "bibel", "biblisch",
        "glauben", "glaube", "schöpfung", "aufersteh", "gnade", "erlösung", "diakon",
        "konfession", "katechism", "synod", "spiritual", "geistlich", "kloster", "mönch",
    ),
    REGIME_NEOLIBERAL: (
        "achtsam", "selbst", "resilien", "bewusst", "glück", "erfolg", "heilung",
        "achtsamkeit", "wohlbefind", "lebenshilf", "potenzial", "stress", "meditat",
        "gelassen", "motivation", "coaching", "therapie", "psycholog", "inner",
        "achtsamkeits", "selbstfürsorg", "selbstoptimier", "persönlichkeit", "ganzheit",
        "transformation", "harmonie", "achtsame", "körper", "seele", "lebenskunst",
    ),
    REGIME_CRITICAL: (
        "säkular", "kritik", "kritisch", "gesellschaft", "diskurs", "macht", "ideolog",
        "aufklär", "modern", "wissenschaft", "soziolog", "philosoph", "demokrat",
        "emanzip", "herrschaft", "rational", "autonom", "ethik", "ethisch", "normativ",
        "öffentlich", "plural", "kultur", "geschicht", "sozial", "system", "theorie",
        "analyse", "struktu", "epistem", "hermeneut", "dekonstruk", "postmodern",
    ),
}

# Disjoint canonical Imprint -> primary Ideological Regime assignment
PUBLISHER_REGIME_MAP: dict[str, set[str]] = {
    REGIME_TRADITIONAL: {
        "Herder", "Patmos", "Vandenhoeck & Ruprecht", "Kohlhammer", "Gütersloher Verlagshaus",
        "St. Benno", "Mohr Siebeck", "Theologischer Verlag Zürich (TVZ)", "Evangelische Verlagsanstalt",
        "SCM / R. Brockhaus", "Schwabenverlag", "Neukirchener", "Friedrich Pustet", "Echter",
        "Matthias Grünewald", "Aschendorff", "Bonifatius", "Calwer", "Ferdinand Schöningh", "Benziger",
        "Katholisches Bibelwerk", "Deutsche Bibelgesellschaft", "Butzon & Bercker", "Christophorus",
    },
    REGIME_NEOLIBERAL: {
        "Kösel", "Gräfe und Unzer (GU)", "Kamphausen", "Kreuz",
        "Scorpio", "Arkana", "Goldmann", "Knaur", "Integral", "Beltz", "Klett-Cotta",
        "Ernst Reinhardt", "Hogrefe", "Junfermann",
        "ownd", "Irisiana", "Kailash", "Lotos", "Schirner", "Windpferd", "Aquamarin", "Theseus",
    },
    REGIME_CRITICAL: {
        "Suhrkamp", "C.H. Beck", "Rowohlt", "S. Fischer", "Campus", "transcript", "Alibri",
        "De Gruyter", "Felix Meiner", "Springer", "Nomos", "Wallstein", "Wagenbach",
        "Kiepenheuer & Witsch", "Insel", "Metzler", "Velbrück", "Konkret", "Karl Alber",
        "Vittorio Klostermann", "Frommann-Holzboog", "Schwabe", "Böhlau", "Fink",
    },
}

PUBLISHER_IMPRINT_LEXICONS: dict[str, tuple[str, list[tuple[str, float]]]] = {
    "herder": (REGIME_TRADITIONAL, [("theologie", 0.036), ("kirche", 0.032), ("liturgie", 0.028), ("sakrament", 0.024), ("seelsorge", 0.021), ("konzil", 0.019)]),
    "benno": (REGIME_TRADITIONAL, [("frömmigkeit", 0.035), ("gebet", 0.031), ("sakrament", 0.027), ("gottesdienst", 0.024), ("heilige", 0.020), ("seelsorge", 0.018)]),
    "patmos": (REGIME_TRADITIONAL, [("religionspädagogik", 0.034), ("bibel", 0.030), ("ökumene", 0.026), ("dialog", 0.023), ("spiritualität", 0.020), ("glaube", 0.018)]),
    "kohlhammer": (REGIME_TRADITIONAL, [("exegese", 0.035), ("dogmatik", 0.031), ("kirchenrecht", 0.027), ("theologie", 0.024), ("systematik", 0.021), ("diakonie", 0.018)]),
    "vandenhoeck": (REGIME_TRADITIONAL, [("evangelisch", 0.035), ("praktische_theologie", 0.031), ("predigt", 0.027), ("gemeinde", 0.024), ("homiletik", 0.020), ("konfession", 0.018)]),
    "mohr": (REGIME_TRADITIONAL, [("dogmengeschichte", 0.036), ("hermeneutik", 0.032), ("rechtsphilosophie", 0.028), ("altes_testament", 0.024), ("exegese", 0.021), ("religionswissenschaft", 0.019)]),
    "gütersloher": (REGIME_TRADITIONAL, [("kirchenmitgliedschaft", 0.035), ("religionsunterricht", 0.031), ("gemeinde", 0.027), ("evangelisch", 0.024), ("lebenswelt", 0.020), ("seelsorge", 0.018)]),
    "brockhaus": (REGIME_TRADITIONAL, [("bibel", 0.036), ("nachfolge", 0.032), ("evangelium", 0.028), ("gebet", 0.024), ("glaube", 0.021), ("gemeindeaufbau", 0.018)]),
    "kösel": (REGIME_NEOLIBERAL, [("achtsamkeit", 0.038), ("resilienz", 0.033), ("selbstfürsorge", 0.029), ("lebenshilfe", 0.025), ("heilung", 0.022), ("inneres_kind", 0.019)]),
    "gu": (REGIME_NEOLIBERAL, [("selbstoptimierung", 0.039), ("wohlbefinden", 0.034), ("stressbewältigung", 0.030), ("glück", 0.026), ("balance", 0.022), ("potenzial", 0.019)]),
    "gräfe": (REGIME_NEOLIBERAL, [("selbstoptimierung", 0.039), ("wohlbefinden", 0.034), ("stressbewältigung", 0.030), ("glück", 0.026), ("balance", 0.022), ("potenzial", 0.019)]),
    "kamphausen": (REGIME_NEOLIBERAL, [("meditation", 0.038), ("bewusstsein", 0.033), ("gegenwart", 0.029), ("spiritualität", 0.025), ("stille", 0.022), ("erwachen", 0.019)]),
    "kreuz": (REGIME_NEOLIBERAL, [("lebenskunst", 0.035), ("trauerbegleitung", 0.031), ("resilienz", 0.027), ("biografiearbeit", 0.024), ("sinnkrise", 0.021), ("gelassenheit", 0.018)]),
    "suhrkamp": (REGIME_CRITICAL, [("säkularisierung", 0.039), ("kritische_theorie", 0.034), ("öffentlichkeit", 0.030), ("moderne", 0.026), ("diskurs", 0.023), ("emanzipation", 0.020)]),
    "beck": (REGIME_CRITICAL, [("kulturgeschichte", 0.036), ("aufklärung", 0.032), ("staatskirchenrecht", 0.028), ("säkularismus", 0.024), ("demokratie", 0.021), ("pluralismus", 0.019)]),
    "rowohlt": (REGIME_CRITICAL, [("religionskritik", 0.036), ("gesellschaftskritik", 0.031), ("ideologie", 0.027), ("autonomie", 0.024), ("moderne", 0.021), ("aufklärung", 0.018)]),
    "fischer": (REGIME_CRITICAL, [("psychoanalyse", 0.035), ("kulturkritik", 0.031), ("gedächtnis", 0.027), ("genealogie", 0.024), ("herrschaft", 0.021), ("subjektivität", 0.018)]),
    "alibri": (REGIME_CRITICAL, [("atheismus", 0.039), ("humanismus", 0.034), ("kirchenkritik", 0.030), ("laizismus", 0.026), ("vernunft", 0.023), ("aufklärung", 0.020)]),
}


def normalize_regime_label(raw_label: str | None) -> str:
    """Normalizes any legacy or abbreviated regime string to one of the 3 canonical Ideological Regimes."""
    if not raw_label:
        return REGIME_TRADITIONAL
    cleaned = str(raw_label).strip()
    if cleaned in LEGACY_REGIME_ALIASES:
        return LEGACY_REGIME_ALIASES[cleaned]
    low = cleaned.lower()
    if "traditional" in low or "ecclesiast" in low or "theolog" in low:
        return REGIME_TRADITIONAL
    if "neoliberal" in low or "self" in low or "optim" in low:
        return REGIME_NEOLIBERAL
    return REGIME_CRITICAL


def infer_imprint_regime(publisher: str, tokens: list[str] | None = None) -> str:
    """
    Infers the primary Ideological Regime (RQ1, RQ2, RQ3) for an Imprint and optional token list.
    """
    pub_low = str(publisher or "").lower()
    scores: dict[str, float] = {r: 0.1 for r in CANONICAL_REGIMES}

    for tok in (tokens or []):
        w = tok.lower()
        for reg_name, lex_set in config.ARCHETYPE_LEXICONS.items():
            if w in lex_set or any(p in lex_set for p in w.split("_")):
                scores[reg_name] += 2.2
        for reg_name, prefixes in ARCHETYPE_STEM_PREFIXES.items():
            if any(w.startswith(pr) for pr in prefixes):
                scores[reg_name] += 0.9

    if any(k in pub_low for k in ("benno", "evangelische", "bibel", "neukirchen", "pustet", "echter", "bonifatius", "calwer", "mohr", "kohlhammer", "herder", "patmos", "vandenhoeck", "gütersloher", "brockhaus")):
        scores[REGIME_TRADITIONAL] += 3.5
    elif any(k in pub_low for k in ("kösel", "gräfe", "unzer", "kamphausen", "kreuz", "scorpio", "arkana", "goldmann", "knaur", "integral", "irisiana", "windpferd", "schirner", "aquamarin")):
        scores[REGIME_NEOLIBERAL] += 3.5
    elif any(k in pub_low for k in ("suhrkamp", "beck", "rowohlt", "fischer", "campus", "transcript", "alibri", "gruyter", "meiner", "springer", "nomos", "wallstein", "wagenbach", "klostermann")):
        scores[REGIME_CRITICAL] += 3.5

    return max(scores.items(), key=lambda x: x[1])[0]


def classify_topic_archetype(keywords_with_weights: list) -> dict:
    """
    Scores a Posterior Topic's top weighted lemmas against the three Ideological Regimes
    using rank-salience weighting, exact lexicon lookup, and morphological stem matching.
    """
    raw_scores: dict[str, float] = {r: 0.0 for r in CANONICAL_REGIMES}
    for rank_idx, item in enumerate(keywords_with_weights):
        if isinstance(item, dict):
            word = str(item.get("word") or item.get("term") or "")
            weight = float(item.get("weight", 0.01))
        else:
            word, weight = str(item[0]), float(item[1])
        w_low = word.lower()
        parts = w_low.split("_")
        rank_multiplier = 1.8 if rank_idx < 3 else (1.35 if rank_idx < 7 else 1.0)
        eff_weight = float(weight) * rank_multiplier

        for archetype, lexicon in config.ARCHETYPE_LEXICONS.items():
            if w_low in lexicon or any(p in lexicon for p in parts):
                raw_scores[archetype] += eff_weight * 2.4
                continue
            prefixes = ARCHETYPE_STEM_PREFIXES.get(archetype, ())
            if any(p.startswith(pref) for p in parts for pref in prefixes):
                raw_scores[archetype] += eff_weight * 1.15

    total_matched = sum(raw_scores.values())
    if total_matched <= 0:
        return {
            "label": "General / Mixed Discourse",
            "confidence": 33.3,
            "scores": {k: 33.3 for k in raw_scores},
        }

    norm_scores = {k: round((v / total_matched) * 100, 1) for k, v in raw_scores.items()}
    dominant = max(norm_scores, key=norm_scores.get)
    return {
        "label": dominant,
        "confidence": norm_scores[dominant],
        "scores": norm_scores,
    }


def get_canonical_taxonomy_payload() -> dict:
    """Returns the canonical Ideological Regime & Imprint taxonomy payload for the API seam."""
    return {
        "canonical_regimes": list(CANONICAL_REGIMES),
        "seed_lexicons": {k: sorted(list(v)) for k, v in config.ARCHETYPE_LEXICONS.items()},
        "religious_boost_keywords": list(config.RELIGIOUS_VOICE_KEYWORDS),
        "publisher_regime_map": {k: sorted(list(v)) for k, v in PUBLISHER_REGIME_MAP.items()},
    }
