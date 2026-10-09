"""The headline numbers in the README (and the submission text, when it's beside this repo) are recomputed from the
committed snapshots, so a published figure can't drift from the data."""

from pathlib import Path

import pytest

from kalaana import views

ROOT = Path(__file__).resolve().parent.parent
TEXTS = [p for p in (ROOT / "README.md", ROOT.parent / "submission" / "description.md") if p.exists()]


def claims() -> list[tuple[str, ...]]:
    """Each figure, in the phrasings the texts use for it (any one must appear)."""
    t = views.totals()
    rto, sro, passport = (views.load(views.CITY, x)["headline"] for x in ("rto", "subregistrar", "passport"))

    def of(n: int, total: int) -> tuple[str, ...]:
        return (f"{n} of {total}",) + ((f"all {total}",) if n == total else ())
    return [
        (f"{t['official']} of {t['listed']} Google Maps listings",),  # 2 of 58
        (f"{t['no_phone']} show",),  # 41 show no phone / none
        of(t["ai"] - t["ai_right"], t["ai"]),  # the AI Overview didn't lead with the office's own number
        (f"{t['searches']} SerpApi searches",),
        of(rto["ai_mode_first_number_right"], rto["ai_mode_answers"]),  # AI Mode, RTOs
        of(sro["ai_mode_first_number_right"], sro["ai_mode_answers"]),  # AI Mode, sub-registrar offices
        (f"{t['bing_no_phone']} show no phone",  # Bing, in total or per office type
         f"{rto['bing_found']} RTOs we could match on Bing, {rto['bing_no_phone']} show no phone"),
        (f"{passport['offices']} passport offices",),
    ]


@pytest.mark.parametrize("path", TEXTS, ids=lambda p: p.name)
def test_published_headline_numbers_match_the_snapshots(path: Path) -> None:
    text = " ".join(path.read_text(encoding="utf-8").split())
    missing = [c for c in claims() if not any(form in text for form in c)]
    assert not missing, f"{path.name} doesn't state these figures as the snapshots compute them: {missing}"
