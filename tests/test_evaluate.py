"""The lexicon's measured accuracy on hand-labelled real reviews.

`rto-reviews-heldout.jsonl` was labelled blind and never used to tune the lexicon, so these
floors guard the reported numbers: a change that makes the lexicon worse fails here.
"""

from kalaana import evaluate
from kalaana.taxonomy import CATEGORIES


def test_labels_are_well_formed() -> None:
    categories = {c.id for c in CATEGORIES}
    for name in ("rto-reviews.jsonl", "rto-reviews-heldout.jsonl"):
        rows = evaluate.load(evaluate.LABELS_DIR / name)
        assert [r["n"] for r in rows] == list(range(1, len(rows) + 1))
        for r in rows:
            ambiguous = {a for a in r["ambiguous"].split(",") if a}
            assert set(r["labels"]) <= categories and ambiguous <= categories, r["n"]
            assert not set(r["labels"]) & ambiguous, r["n"]


def test_held_out_accuracy_does_not_regress() -> None:
    results = evaluate.evaluate(evaluate.load(evaluate.LABELS_DIR / "rto-reviews-heldout.jsonl"))
    precision, recall = evaluate.micro_average(results)
    assert precision >= 0.948 and recall >= 0.743, (precision, recall)  # 55 of 58 flags right, 55 of 74 reports found


def test_precision_and_recall_arithmetic() -> None:
    rows = [
        {"n": 1, "text": "They asked for a bribe", "labels": ["bribe"], "ambiguous": ""},
        {"n": 2, "text": "Very helpful staff", "labels": [], "ambiguous": ""},
        {"n": 3, "text": "Pay money or wait", "labels": ["bribe"], "ambiguous": ""},
        {"n": 4, "text": "bribe?", "labels": [], "ambiguous": "bribe"},
    ]
    results = evaluate.evaluate(rows)
    bribe, helpful = results["bribe"], results["helpful"]
    assert (bribe.true_positives, bribe.false_negatives, bribe.ambiguous) == ([1], [3], 1)
    assert bribe.precision == 1 and bribe.recall == 0.5
    assert helpful.false_positives == [2] and helpful.precision == 0 and helpful.recall is None
