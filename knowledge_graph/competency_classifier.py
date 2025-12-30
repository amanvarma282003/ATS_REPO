from __future__ import annotations

from typing import Any, Dict, List

CATEGORY_WEIGHTS: Dict[str, float] = {
    "ML_AI": 1.0,
    "TECHNICAL_CORE": 1.0,
    "PLATFORM": 0.9,
    "RELIABILITY": 0.85,
    "PROCESS": 0.75,
    "COLLABORATION": 0.6,
    "GENERAL": 0.8,
}

CATEGORY_THRESHOLDS: Dict[str, float] = {
    "ML_AI": 0.38,
    "TECHNICAL_CORE": 0.38,
    "PLATFORM": 0.37,
    "RELIABILITY": 0.35,
    "PROCESS": 0.33,
    "COLLABORATION": 0.3,
    "GENERAL": 0.35,
}

def _canonicalize_name(name: str) -> str:
    return name.strip()


def _classify_category(name: str, description: str) -> str:
    return "GENERAL"


def _clamp(value: float, *, min_value: float = 0.3, max_value: float = 1.2) -> float:
    return max(min_value, min(max_value, value))


def _ensure_dict(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        return dict(entry)
    return {"name": str(entry)}


def enrich_competency(entry: Any, *, importance: str) -> Dict[str, Any]:
    comp = _ensure_dict(entry)
    name = (comp.get("name") or comp.get("title") or "").strip()
    description = (comp.get("description") or "").strip()
    category = comp.get("category") or _classify_category(name, description)
    weight = float(comp.get("weight") or CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["GENERAL"]))
    threshold = float(comp.get("match_threshold") or CATEGORY_THRESHOLDS.get(category, CATEGORY_THRESHOLDS["GENERAL"]))

    enriched = dict(comp)
    enriched.update({
        "name": name,
        "description": description,
        "category": category,
        "weight": _clamp(weight),
        "importance": importance.upper(),
        "match_threshold": _clamp(threshold, min_value=0.25, max_value=0.5),
        "canonical_name": comp.get("canonical_name") or _canonicalize_name(name),
    })
    return enriched


def normalize_competencies(entries: List[Any], *, importance: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in entries:
        normalized.append(enrich_competency(entry, importance=importance))
    return normalized