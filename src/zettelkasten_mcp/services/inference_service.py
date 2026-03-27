"""Link-type inference service using pattern-matching heuristics."""

import re

from zettelkasten_mcp.models.schema import Note

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "do",
        "for",
        "from",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
    },
)

# Pattern signals for each link type
_PATTERNS: dict[str, list[str]] = {
    "extends": [
        "build",
        "building on",
        "expand",
        "extends",
        "extension",
        "further",
        "additional",
        "elaborat",
        "develops",
        "adds to",
        "builds upon",
        "based on",
    ],
    "supports": [
        "evidence",
        "demonstrates",
        "confirms",
        "validates",
        "proves",
        "shows",
        "supports",
        "corroborat",
        "consistent with",
        "in agreement",
    ],
    "contradicts": [
        "contradict",
        "disagree",
        "oppose",
        "conflict",
        "refutes",
        "challenges",
        "against",
        "however",
        "in contrast",
        "alternatively",
        "whereas",
        "despite",
    ],
    "questions": [
        "question",
        "doubt",
        "uncertain",
        "unclear",
        "wonder",
        "unclear",
        "investigate",
        "explore",
        "whether",
        "why",
        "how does",
    ],
    "refines": [
        "refine",
        "clarif",
        "precise",
        "specific",
        "improve",
        "narrow",
        "exactly",
        "more precise",
        "clearer version",
        "correction",
    ],
    "related": [
        "related",
        "see also",
        "also",
        "similar",
        "connect",
        "link",
        "associat",
    ],
}

_LOW_CONFIDENCE_THRESHOLD = 0.4
_MAX_SUGGESTIONS = 3
_MIN_WORD_LENGTH = 2


def _tokenize(text: str) -> set[str]:
    """Return lowercased, non-stopword word tokens from *text*."""
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > _MIN_WORD_LENGTH}


def _score_text(text: str, patterns: list[str]) -> float:
    """Return a [0, 1] score for how well *text* matches *patterns*."""
    if not text:
        return 0.0
    lower = text.lower()
    hits = sum(1 for p in patterns if p in lower)
    return min(1.0, hits / max(len(patterns) * 0.3, 1))


class InferenceService:
    """Infer the most likely link type between two notes."""

    def suggest_link_type(self, source: Note, target: Note) -> dict:
        """Suggest the top link types for a source -> target relationship.

        Uses keyword pattern-matching against both notes' content and title.
        No ML dependency; runs in O(|patterns| x |content|) time.

        Args:
            source: The note creating the link.
            target: The note being linked to.

        Returns:
            Dict with:
            - ``suggestions``: list of ``{"link_type": str, "confidence": float}``
              sorted highest-first (up to _MAX_SUGGESTIONS entries)
            - ``low_confidence``: True if all scores < 0.4
        """
        combined_source = f"{source.title} {source.content}"
        combined_target = f"{target.title} {target.content}"
        combined = f"{combined_source} {combined_target}"

        scores: dict[str, float] = {}
        for link_type, patterns in _PATTERNS.items():
            s = _score_text(combined, patterns)
            if s > 0:
                scores[link_type] = s

        # Always include "reference" as a baseline fallback
        if "reference" not in scores:
            scores["reference"] = 0.1

        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:_MAX_SUGGESTIONS]  # noqa: E501
        suggestions = [
            {"link_type": lt, "confidence": round(score, 3)}
            for lt, score in sorted_types
        ]

        low_confidence = all(s["confidence"] < _LOW_CONFIDENCE_THRESHOLD for s in suggestions)  # noqa: E501

        return {
            "suggestions": suggestions,
            "low_confidence": low_confidence,
        }
