from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from hyperon import MeTTa

from movie_query_parser import ParsedMovieQuery, parse_movie_query


@dataclass(frozen=True)
class Recommendation:
    title: str
    score: int
    matched_features: tuple[str, ...]


class SymbolicMovieRecommender:
    def __init__(self, knowledge_base_path: Path | None = None) -> None:
        base_path = knowledge_base_path or Path(__file__).parent / "movie_data.metta"
        self.metta = MeTTa()
        self.metta.run(base_path.read_text())
        self.movies = self._load_movies()
        self.movie_features = {
            movie: self._load_features_for_movie(movie) for movie in self.movies
        }

    def _run_match(self, pattern: str, template: str) -> list[str]:
        query = f"!(match &self {pattern} {template})"
        rows = self.metta.run(query)
        values: list[str] = []
        for row in rows:
            for atom in row:
                values.append(str(atom))
        return values

    def _load_movies(self) -> list[str]:
        return sorted(set(self._run_match("(movie $title)", "$title")))

    def _load_features_for_movie(self, movie: str) -> dict[str, set[str]]:
        rows = self.metta.run(
            f"!(match &self (movie-feature {movie} $kind $value) ($kind $value))"
        )
        features: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            for atom in row:
                text = str(atom).strip("()")
                parts = text.split()
                if len(parts) != 2:
                    continue
                kind, value = parts
                features[kind].add(value)
        return dict(features)

    def describe_movie(self, movie: str) -> dict[str, list[str]]:
        if movie not in self.movie_features:
            raise ValueError(f"Unknown movie: {movie}")
        return {
            feature_type: sorted(values)
            for feature_type, values in sorted(self.movie_features[movie].items())
        }

    def recommend_like(self, movie: str, limit: int = 5) -> list[Recommendation]:
        if movie not in self.movie_features:
            raise ValueError(f"Unknown movie: {movie}")

        candidates = set(self.movies) - {movie}
        return self._score_candidates_from_likes([movie], candidates, limit=limit)

    def recommend_from_query(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[ParsedMovieQuery, list[Recommendation]]:
        parsed_query = parse_movie_query(query, default_limit=limit)
        recommendations = self._score_candidates_from_preferences(
            parsed_query.preferences,
            candidates=set(self.movies),
            limit=parsed_query.limit,
            excluded_features=parsed_query.exclusions,
        )
        return parsed_query, recommendations

    def _query_shared_feature_paths(self, movie: str) -> list[tuple[str, str, str]]:
        paths: list[tuple[str, str, str]] = []
        movie_features = self.movie_features[movie]
        for candidate, features in self.movie_features.items():
            if candidate == movie:
                continue
            for feature_type, values in movie_features.items():
                for value in values:
                    if value in features.get(feature_type, set()):
                        paths.append((candidate, feature_type, value))
        return paths

    def _query_movies_with_feature(self, feature_type: str, value: str) -> set[str]:
        rows = self.metta.run(f"!(moviesWithFeature {feature_type} {value} &self)")
        matches: set[str] = set()
        for row in rows:
            for atom in row:
                matches.add(str(atom))
        return matches

    def _score_candidates_from_preferences(
        self,
        preferences: dict[str, set[str]],
        candidates: set[str],
        limit: int,
        excluded_features: dict[str, set[str]] | None = None,
    ) -> list[Recommendation]:
        excluded_features = excluded_features or {}
        preference_list = self._preferences_to_metta_list(preferences)
        matched_labels = self._collect_preference_labels(preferences)
        recommendations: list[Recommendation] = []

        for candidate in sorted(candidates):
            candidate_features = self.movie_features[candidate]
            if self._is_excluded(candidate_features, excluded_features):
                continue
            score = self._run_int_query(
                f"!(scoreCandidateFromPrefs {candidate} {preference_list} &self)"
            )
            if score <= 0:
                continue
            labels = tuple(
                sorted(
                    label
                    for label in matched_labels
                    if self._candidate_has_label(candidate, label)
                )
            )
            recommendations.append(
                Recommendation(title=candidate, score=score, matched_features=labels)
            )
        recommendations.sort(
            key=lambda item: (-item.score, -len(item.matched_features), item.title)
        )
        return recommendations[:limit]

    def _score_candidates_from_likes(
        self,
        liked_movies: Iterable[str],
        candidates: set[str],
        limit: int,
    ) -> list[Recommendation]:
        liked_list = self._to_metta_list(liked_movies)
        recommendations: list[Recommendation] = []
        for candidate in sorted(candidates):
            score = self._run_int_query(
                f"!(scoreCandidateFromLikes {candidate} {liked_list} &self)"
            )
            if score <= 0:
                continue
            labels = self._collect_shared_labels_for_likes(liked_movies, candidate)
            recommendations.append(
                Recommendation(title=candidate, score=score, matched_features=labels)
            )
        recommendations.sort(
            key=lambda item: (-item.score, -len(item.matched_features), item.title)
        )
        return recommendations[:limit]

    def _run_int_query(self, query: str) -> int:
        rows = self.metta.run(query)
        for row in rows:
            for atom in row:
                return int(str(atom))
        return 0

    def _to_metta_list(self, items: Iterable[str]) -> str:
        values = list(items)
        if not values:
            return "()"
        return f"({' '.join(values)})"

    def _preferences_to_metta_list(self, preferences: dict[str, set[str]]) -> str:
        entries: list[str] = []
        for feature_type, values in sorted(preferences.items()):
            for value in sorted(values):
                entries.extend([feature_type, value])
        if not entries:
            return "()"
        return f"({' '.join(entries)})"

    def _collect_preference_labels(self, preferences: dict[str, set[str]]) -> set[str]:
        return {
            f"{feature_type}:{value}"
            for feature_type, values in preferences.items()
            for value in values
        }

    def _candidate_has_label(self, candidate: str, label: str) -> bool:
        feature_type, value = label.split(":", 1)
        return value in self.movie_features[candidate].get(feature_type, set())

    def _collect_shared_labels_for_likes(
        self,
        liked_movies: Iterable[str],
        candidate: str,
    ) -> tuple[str, ...]:
        labels: set[str] = set()
        for movie in liked_movies:
            for (
                matched_candidate,
                feature_type,
                value,
            ) in self._query_shared_feature_paths(movie):
                if matched_candidate == candidate:
                    labels.add(f"{feature_type}:{value}")
        return tuple(sorted(labels))

    def _is_excluded(
        self,
        candidate_features: dict[str, set[str]],
        excluded_features: dict[str, set[str]],
    ) -> bool:
        for feature_type, banned_values in excluded_features.items():
            overlap = banned_values & candidate_features.get(feature_type, set())
            if overlap:
                return True
        return False


def format_recommendations(title: str, recommendations: list[Recommendation]) -> str:
    lines = [title]
    for index, recommendation in enumerate(recommendations, start=1):
        reasons = ", ".join(recommendation.matched_features)
        lines.append(
            f"{index}. {recommendation.title} | score={recommendation.score} | matched={reasons}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    recommender = SymbolicMovieRecommender()

    print("Available movies:")
    print(", ".join(recommender.movies))
    print()

    similar_to_inception = recommender.recommend_like("Inception", limit=5)
    print(format_recommendations("Because you liked Inception:", similar_to_inception))
    print()

    parsed_query, natural_language_recommendations = recommender.recommend_from_query(
        "Recommend 3 cerebral sci-fi movies with family themes but not dark ones.",
        limit=5,
    )
    print(parsed_query)
    print(
        format_recommendations(
            "Natural-language query recommendations:",
            natural_language_recommendations,
        )
    )
