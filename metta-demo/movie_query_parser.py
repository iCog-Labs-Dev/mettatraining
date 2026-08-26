from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedMovieQuery:
    raw_query: str
    preferences: dict[str, set[str]]
    exclusions: dict[str, set[str]]
    limit: int


FEATURE_SYNONYMS = {
    "Genre": {
        "sci fi": "SciFi",
        "sci-fi": "SciFi",
        "science fiction": "SciFi",
        "thriller": "Thriller",
        "action": "Action",
        "drama": "Drama",
        "romance": "Romance",
        "musical": "Musical",
        "fantasy": "Fantasy",
        "adventure": "Adventure",
        "mystery": "Mystery",
        "comedy": "Comedy",
        "crime": "Crime",
        "noir": "Noir",
    },
    "Theme": {
        "mind bending": "MindBending",
        "mind-bending": "MindBending",
        "heist": "Heist",
        "space": "SpaceExploration",
        "space exploration": "SpaceExploration",
        "family": "Family",
        "rebellion": "Rebellion",
        "identity": "Identity",
        "dystopia": "Dystopia",
        "first contact": "FirstContact",
        "language": "Language",
        "survival": "Survival",
        "vigilantism": "Vigilantism",
        "chaos": "Chaos",
        "ambition": "Ambition",
        "love": "Love",
        "coming of age": "ComingOfAge",
        "coming-of-age": "ComingOfAge",
        "magic": "Magic",
        "class conflict": "ClassConflict",
        "deception": "Deception",
        "friendship": "Friendship",
        "memory": "Memory",
    },
    "Tone": {
        "cerebral": "Cerebral",
        "emotional": "Emotional",
        "atmospheric": "Atmospheric",
        "kinetic": "Kinetic",
        "dark": "Dark",
        "hopeful": "Hopeful",
        "whimsical": "Whimsical",
        "playful": "Playful",
    },
    "Setting": {
        "urban": "Urban",
        "city": "Urban",
        "space": "Space",
        "contemporary": "Contemporary",
        "desert": "Desert",
        "otherworld": "Otherworld",
        "domestic": "Domestic",
        "european": "European",
    },
    "Era": {
        "modern": "Modern",
        "future": "Future",
        "period": "Period",
        "timeless": "Timeless",
    },
}


def parse_movie_query(text: str, default_limit: int = 5) -> ParsedMovieQuery:
    query = text.strip()
    if not query:
        raise ValueError("Enter a movie preference query.")

    normalized = _normalize(query)
    exclusions = _extract_exclusions(normalized)
    positive_text = _strip_exclusion_clauses(normalized)
    preferences = _extract_features(positive_text)
    limit = _extract_limit(normalized, default_limit)

    if not preferences:
        raise ValueError(
            "I could not map that request to known movie features. "
            "Try terms like sci-fi, cerebral, family, dystopia, whimsical, or modern."
        )

    return ParsedMovieQuery(
        raw_query=query,
        preferences=preferences,
        exclusions=exclusions,
        limit=limit,
    )


def _normalize(text: str) -> str:
    lowered = text.lower()
    lowered = lowered.replace("/", " ")
    lowered = re.sub(r"[^a-z0-9\s-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _extract_features(text: str) -> dict[str, set[str]]:
    matched: dict[str, set[str]] = {}
    for feature_type, synonyms in FEATURE_SYNONYMS.items():
        values = {
            canonical
            for phrase, canonical in synonyms.items()
            if re.search(rf"\b{re.escape(phrase)}\b", text)
        }
        if values:
            matched[feature_type] = values
    return matched


def _extract_exclusions(text: str) -> dict[str, set[str]]:
    exclusions: dict[str, set[str]] = {}
    clauses = re.findall(r"(?:not|without|exclude|excluding)\s+([a-z0-9\s-]+)", text)
    for clause in clauses:
        clause_matches = _extract_features(clause)
        for feature_type, values in clause_matches.items():
            exclusions.setdefault(feature_type, set()).update(values)
    return exclusions


def _strip_exclusion_clauses(text: str) -> str:
    return re.sub(r"(?:not|without|exclude|excluding)\s+[a-z0-9\s-]+", " ", text).strip()


def _extract_limit(text: str, default_limit: int) -> int:
    match = re.search(r"(?:top|show|give me|recommend)\s+(\d+)", text)
    if match:
        return max(1, min(10, int(match.group(1))))
    return default_limit
