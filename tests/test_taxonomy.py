"""The issue lexicon: every category in at least two languages, plus the traps found in real reviews.

English examples are short phrases of the kind found in the collected reviews. The other
languages are written for these tests; their real-world accuracy is measured in the
evaluation, not claimed here.
"""

import re

import pytest

from kalaana import taxonomy
from kalaana.taxonomy import BY_ID, CATEGORIES, classify

# (category, language, text that must hit, the exact words the hit should cover)
CASES = [
    ("unreachable", "en", "Worst part is that their land line numbers is not working", "land line numbers is not working"),
    ("unreachable", "en", "No one picks phone. Pathetic service", "No one picks phone"),
    ("unreachable", "en", "They don't attend phone calls", "don't attend phone"),
    ("unreachable", "kn-latn", "Phone receive madalla. Bad service.", "Phone receive madalla"),
    ("unreachable", "hi-latn", "office ka phone nahi uthate", "phone nahi uthate"),
    ("unreachable", "hi", "दफ्तर में कोई फोन नहीं उठाता", "फोन नहीं उठा"),
    ("bribe", "en", "They ask 10 rs 20 rs bribe full beggars", "bribe"),
    ("bribe", "en", "they kept calling and at last demanded 5000", "demanded 5000"),
    ("bribe", "kn", "ಇಲ್ಲಿ ಲಂಚ ಇಲ್ಲದೆ ಕೆಲಸ ಆಗುವುದಿಲ್ಲ", "ಲಂಚ"),
    ("bribe", "kn-latn", "illi lancha kodbeku", "lancha"),
    ("bribe", "hi", "बिना रिश्वत के कोई काम नहीं होता", "रिश्वत"),
    ("bribe", "ta", "லஞ்சம் கேட்கிறார்கள்", "லஞ்ச"),
    ("bribe", "te", "లంచాలు అడుగుతారు", "లంచ"),
    ("tout", "en", "it's basically run by middlemen", "middlemen"),
    ("tout", "kn", "ಮಧ್ಯವರ್ತಿಗಳ ಮೂಲಕ ಮಾತ್ರ ಕೆಲಸ", "ಮಧ್ಯವರ್ತಿ"),
    ("tout", "kn", "ಏಜೆಂಟರು ಎಲ್ಲಾ ಕಡೆ ಇದ್ದಾರೆ", "ಏಜೆಂಟರು"),
    ("tout", "kn-latn", "dallaligalu tumba", "dallaligalu"),
    ("tout", "hi", "यहाँ दलाल ही सब करते हैं", "दलाल"),
    ("tout", "ta", "ஏஜென்ட் மூலம் தான் வேலை", "ஏஜென்ட்"),
    ("tout", "te", "దళారీ లేకుండా పని కాదు", "దళారీ"),
    ("delay", "en", "the application has still been pending for more than 3 months now", "pending for more than 3 months"),
    ("delay", "en", "LL test has been completed, 20days also over, still LL is not approved", "20days also over"),
    ("delay", "en", "It's been 8 months, not yet got rc", "It's been 8 months"),
    ("delay", "kn", "ಅರ್ಜಿ ವಿಳಂಬವಾಗಿದೆ", "ವಿಳಂಬ"),
    ("delay", "hi", "काम में बहुत देरी हो रही है", "देरी"),
    ("delay", "ta", "மிகவும் தாமதமாக வேலை", "தாமத"),
    ("staff", "en", "Terrible people. Very rude, they behave well if you go with an agent", "rude"),
    ("staff", "en", "The officer was talking rudely", "rudely"),
    ("staff", "en", "They just waste everyone's time", "waste everyone's time"),
    ("staff", "kn", "ಸಿಬ್ಬಂದಿ ಅಸಭ್ಯವಾಗಿ ವರ್ತಿಸುತ್ತಾರೆ", "ಅಸಭ್ಯ"),
    ("staff", "hi", "कर्मचारी बहुत लापरवाह हैं", "लापरवाह"),
    ("staff", "te", "సిబ్బంది నిర్లక్ష్యంగా ఉన్నారు", "నిర్లక్ష్య"),
    ("portal", "en", "make public wait saying server down everyday", "server down"),
    ("portal", "en", "The Vahan portal was another challenge. It frequently failed during payment", "Vahan portal was another challenge. It frequently failed"),
    ("portal", "kn", "ಸರ್ವರ್ ಡೌನ್ ಎಂದು ಹೇಳಿ ಕಳುಹಿಸಿದರು", "ಸರ್ವರ್ ಡೌನ್"),
    ("portal", "hi", "सर्वर डाउन है बोलकर वापस भेज दिया", "सर्वर डाउन"),
    ("closed", "en", "This is my 10th visit to this branch, and once again, operations are completely shut down", "operations are completely shut down"),
    ("closed", "en", "The staff were all assigned to SIR (Special Intensive Revision) duty", "assigned to SIR (Special Intensive Revision) duty"),
    ("closed", "en", "Time waste only no one there 4 to 5pm", "no one there"),
    ("closed", "kn", "ಕಚೇರಿ ಮುಚ್ಚಲಾಗಿದೆ", "ಮುಚ್ಚಲಾಗಿದೆ"),
    ("closed", "hi", "दोपहर में ऑफिस बंद था", "बंद था"),
    ("queue", "en", "omg i waited 2 hours to complete my work", "waited 2 hours"),
    ("queue", "en", "there will be 4-5 queues", "4-5 queues"),
    ("queue", "en", "always overcrowded on Mondays", "always overcrowded"),
    ("queue", "kn", "ದೊಡ್ಡ ಸರತಿ ಸಾಲು ಇತ್ತು", "ಸರತಿ"),
    ("queue", "hi", "बहुत लंबी लाइन थी", "लंबी लाइन"),
    ("queue", "te", "క్యూలో రెండు గంటలు", "క్యూ"),
    ("helpful", "en", "Very helpful staff, exceptional for a government office", "Very helpful"),
    ("helpful", "en", "RTO and his team were very prompt and helpful", "very prompt"),
    ("helpful", "kn", "ಸಿಬ್ಬಂದಿ ಉತ್ತಮ ಸೇವೆ ನೀಡಿದರು", "ಉತ್ತಮ ಸೇವೆ"),
    ("helpful", "hi", "स्टाफ बहुत मददगार था", "मददगार"),
    ("helpful", "ta", "அவர்கள் நல்ல சேவை தந்தார்கள்", "நல்ல சேவை"),
]


@pytest.mark.parametrize(("category", "language", "text", "words"), CASES)
def test_category_hits_with_exact_evidence(category: str, language: str, text: str, words: str) -> None:
    hit = classify(text).get(category)
    assert hit is not None, f"{category} missed: {text}"
    assert hit.text == words and text[hit.start:hit.end] == words  # evidence is a verbatim span
    assert hit.language == language


def test_every_category_is_tested_in_two_languages() -> None:
    languages = {c.id: {lang for cat, lang, *_ in CASES if cat == c.id} for c in CATEGORIES}
    assert all(len(langs) >= 2 and langs - {"en"} for langs in languages.values()), languages


def test_every_pattern_compiles() -> None:
    for category in CATEGORIES:
        for pattern in category.patterns:
            re.compile(pattern.regex)
        for exception in category.exceptions:
            re.compile(exception)
    assert len(BY_ID) == len(CATEGORIES) == 9 and {c.polarity for c in CATEGORIES} == {"problem", "positive"}


# Denials are not reports (most of the bribe and agent false positives in real reviews)


@pytest.mark.parametrize(
    "text",
    [
        "Didn't have to pay any bribe",
        "Did not have to pay a single Rupee as bribe",
        "They never asked me for a bribe",
        "no one asks for bribe here",
        "I paid no bribe to any agent",
        "no need to involve an agent",
        "Never felt the need for an agent",
        "didn't go through any middlemen",
        "I paid no bribe and nothing bad happened",  # "nothing" here doesn't turn it into a claim
        "i didnt engage any agent for this",
        "wasn't helpful at all",
        "None of these agents are helpful or trustworthy",
        "completed without paying any bribe and without using an agent",  # two denials, not a claim
    ],
)
def test_english_denials(text: str) -> None:
    assert not ({"bribe", "tout", "helpful"} & set(classify(text))), classify(text)


@pytest.mark.parametrize(
    "text",
    [
        "Without extra amount and middlemen, no application is accepted.",
        "Not a single work is done here without bribe through middlemen",
    ],
)
def test_denials_that_are_really_claims(text: str) -> None:
    assert {"bribe", "tout"} <= set(classify(text))


@pytest.mark.parametrize("text", ["ಲಂಚ ಕೊಡಬೇಕಾಗಿಲ್ಲ", "रिश्वत नहीं ली", "lancha illa", "बिना रिश्वत काम हो गया", "உதவி செய்யவில்லை"])
def test_denials_in_other_languages(text: str) -> None:
    assert not ({"bribe", "helpful"} & set(classify(text))), classify(text)


# Traps found while reading the collected reviews


@pytest.mark.parametrize(
    "text",
    [
        "It took around 10 to 15 minutes, and everything was done",  # fast, not a queue
        "It took me nearly 1 hour to complete the process",
        "He took 10,000rs for the transfer",  # an agent's fee, not a queue or a bribe demand
        "they demanded 2 documents and asked for 3 photos",  # not money
        "despite the weekend crowd it was manageable",
        "Stand in line for clicking picture, then go to counter 5",  # a how-to step
        "1 star is also waste of rating",  # not about staff
        "U can definitely notice a change in the attitude of the officials",  # praise
        "Thanks to the reviews which helped me",  # thanks to other reviewers
        "un-cooperative staff",
        "RTO office closed on 2nd and 4th Saturday",  # the official holiday rule
        "On 2nd and 4th Saturdays the RTO is closed",
        "Number mentioned on website not working",  # a phone number, not the portal
        "token number not working",
        "phone pay not working",
        "ಲಂಚ್ ಬ್ರೇಕ್ ಇತ್ತು",  # "lunch break", not ಲಂಚ (bribe)
        "వరుసగా మూడు రోజులు",  # "three days in a row", not a queue
    ],
)
def test_traps_do_not_hit(text: str) -> None:
    hits = set(classify(text))
    assert not ({"queue", "bribe", "staff", "helpful", "tout", "closed", "portal", "unreachable"} & hits), hits


def test_sarcasm_in_one_star_reviews_is_not_praise() -> None:
    text = "Very efficient office, took 3 months for an LL"
    assert "helpful" in classify(text, rating=4)
    assert "helpful" not in classify(text, rating=1) and "delay" in classify(text, rating=1)


def test_reviewers_own_words_are_preferred_and_tagged() -> None:
    hits = classify("Poor management, bribe needed", original="ಲಂಚ ಬೇಕು")
    assert (hits["bribe"].language, hits["bribe"].text, hits["bribe"].source) == ("kn", "ಲಂಚ", "original")
    assert classify("bribe needed")["bribe"].source == "text"


def test_one_hit_per_category_earliest_first() -> None:
    hits = taxonomy.find("Agents everywhere. Bribe at every table, more agents later.")
    assert [h.category for h in hits] == ["tout", "bribe"] and hits[0].text == "Agents"
