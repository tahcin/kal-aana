"""Measure the issue lexicon against hand-labelled reviews (data/labels/*.jsonl).

For each category: precision (of the reviews the lexicon flags, how many really report it)
and recall (of the reviews that really report it, how many the lexicon flags). A category a
labeller marked ambiguous for a review is left out of that review's counts.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from . import taxonomy
from .paths import DATA_DIR

LABELS_DIR: Final = DATA_DIR / "labels"


@dataclass
class CategoryResult:
    category: str
    true_positives: list[int] = field(default_factory=list)  # review numbers
    false_positives: list[int] = field(default_factory=list)
    false_negatives: list[int] = field(default_factory=list)
    ambiguous: int = 0

    @property
    def precision(self) -> float | None:
        flagged = len(self.true_positives) + len(self.false_positives)
        return len(self.true_positives) / flagged if flagged else None

    @property
    def recall(self) -> float | None:
        actual = len(self.true_positives) + len(self.false_negatives)
        return len(self.true_positives) / actual if actual else None

    @property
    def support(self) -> int:
        return len(self.true_positives) + len(self.false_negatives)


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


Predictor = Callable[[dict[str, Any]], set[str]]


def lexicon(row: dict[str, Any]) -> set[str]:
    return set(taxonomy.classify(row["text"], row.get("text_original", ""), row.get("rating")))


def evaluate(rows: Iterable[dict[str, Any]], predict: Predictor = lexicon) -> dict[str, CategoryResult]:
    """Score a predictor (the lexicon by default, or a cached LLM reading) against labelled rows."""
    results = {c.id: CategoryResult(c.id) for c in taxonomy.CATEGORIES}
    for row in rows:
        predicted = predict(row)
        actual = set(row["labels"])
        ambiguous = {a for a in row.get("ambiguous", "").split(",") if a}
        for category, result in results.items():
            if category in ambiguous:
                result.ambiguous += 1
            elif category in predicted and category in actual:
                result.true_positives.append(row["n"])
            elif category in predicted:
                result.false_positives.append(row["n"])
            elif category in actual:
                result.false_negatives.append(row["n"])
    return results


def micro_average(results: dict[str, CategoryResult]) -> tuple[float, float]:
    tp = sum(len(r.true_positives) for r in results.values())
    fp = sum(len(r.false_positives) for r in results.values())
    fn = sum(len(r.false_negatives) for r in results.values())
    return (tp / (tp + fp) if tp + fp else 0.0), (tp / (tp + fn) if tp + fn else 0.0)
