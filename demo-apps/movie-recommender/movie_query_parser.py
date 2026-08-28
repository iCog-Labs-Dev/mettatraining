from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

KEY = (
    os.getenv("NVIDIA_API_KEY")
    or os.getenv("NEMOTRON_API_KEY")
    or os.getenv("AI_API_KEY")
)
MODEL_NAME = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
API_BASE_URL = os.getenv(
    "NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1"
).rstrip("/")


@dataclass(frozen=True)
class ParsedMovieQuery:
    raw_query: str
    preferences: dict[str, set[str]]
    exclusions: dict[str, set[str]]
    limit: int


FEATURE_VALUES: dict[str, set[str]] = {
    "Genre": {
        "SciFi", "Thriller", "Drama", "Action", "Adventure", "Noir",
        "Romance", "Musical", "Fantasy", "Mystery", "Comedy", "Crime",
    },
    "Theme": {
        "MindBending", "Heist", "SpaceExploration", "Family", "Rebellion",
        "Identity", "Dystopia", "FirstContact", "Language", "Survival",
        "Vigilantism", "Chaos", "Ambition", "Love", "ComingOfAge", "Magic",
        "ClassConflict", "Deception", "Friendship", "Memory",
    },
    "Tone": {
        "Cerebral", "Emotional", "Atmospheric", "Kinetic", "Dark",
        "Hopeful", "Whimsical", "Playful",
    },
    "Setting": {
        "Urban", "Space", "Contemporary", "Desert", "Otherworld",
        "Domestic", "European",
    },
    "Era": {
        "Modern", "Future", "Period", "Timeless",
    },
}

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

SYSTEM_PROMPT = (
    "You convert natural-language movie requests into a compact JSON object for a "
    "movie recommendation engine.\n\n"
    "You may only use these feature types and exact canonical values:\n"
    + "\n".join(f"{kind}: {', '.join(sorted(values))}" for kind, values in sorted(FEATURE_VALUES.items()))
    + "\n\n"
    "Interpret the request into two buckets:\n"
    "- preferences: features the user WANTS\n"
    "- exclusions: features the user does NOT want (e.g. after 'not', 'without', 'avoid')\n"
    "Detect the requested result count ('recommend 3', 'top 5', 'show 5') as limit.\n"
    "Use exactly these keys in preferences/exclusions: Genre, Theme, Tone, Setting, Era. "
    "Do not pluralize the keys.\n\n"
    'Reply with ONLY one JSON object, no explanation and no markdown, in exactly this shape '
    'using the canonical values above:\n'
    '{"preferences": {"Genre": ["SciFi"], "Tone": ["Cerebral"]}, "exclusions": {"Tone": ["Dark"]}, "limit": 3}\n'
    "Use empty object {} or empty list [] when a bucket has no entries."
)


def parse_movie_query(text: str, default_limit: int = 5) -> ParsedMovieQuery:
    query = text.strip()
    if not query:
        raise ValueError("Enter a movie preference query.")

    try:
        parsed = _parse_with_llm(query, default_limit)
        if parsed.preferences:
            return parsed
    except Exception:
        pass

    return _parse_with_regex(query, default_limit)


def _call_llm(query: str) -> dict:
    if not KEY:
        raise RuntimeError("No API key available for the LLM parser")

    response = requests.post(
        f"{API_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "temperature": 0,
            "max_tokens": 2000,
            "stream": False,
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"NVIDIA API request failed with status {response.status_code}: "
            f"{response.text.strip()}"
        )
    return response.json()


def _extract_text(resp: dict) -> str:
    choices = resp.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "".join(parts)
    if "text" in resp:
        return str(resp["text"])
    return str(resp)


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object in model output")
    return json.loads(text[start : end + 1])


def _canonicalize(feature_type: str, value: str) -> tuple[str, str] | None:
    normalized_type = feature_type.lower().rstrip("s")
    for kind, allowed in FEATURE_VALUES.items():
        if kind.lower().rstrip("s") == normalized_type:
            for candidate in allowed:
                if candidate.lower() == value.lower():
                    return kind, candidate
            return None
    return None


def _parse_with_llm(query: str, default_limit: int) -> ParsedMovieQuery:
    payload = _extract_json(_extract_text(_call_llm(query)))

    preferences: dict[str, set[str]] = {}
    exclusions: dict[str, set[str]] = {}

    for bucket, target in (
        (payload.get("preferences"), preferences),
        (payload.get("exclusions"), exclusions),
    ):
        if not isinstance(bucket, dict):
            continue
        for feature_type, values in bucket.items():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                canonical = _canonicalize(feature_type, str(value))
                if canonical:
                    kind, canonical_value = canonical
                    target.setdefault(kind, set()).add(canonical_value)

    limit = default_limit
    raw_limit = payload.get("limit")
    if raw_limit is not None:
        try:
            limit = max(1, min(10, int(raw_limit)))
        except (TypeError, ValueError):
            limit = default_limit

    return ParsedMovieQuery(
        raw_query=query,
        preferences=preferences,
        exclusions=exclusions,
        limit=limit,
    )


def _parse_with_regex(text: str, default_limit: int) -> ParsedMovieQuery:
    normalized = _normalize(text)
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
        raw_query=text,
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
