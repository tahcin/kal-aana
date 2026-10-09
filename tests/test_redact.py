"""Quotes never show a person's name or a private mobile number.

The sentences follow the patterns found in the collected reviews; the names in them are
made up for these tests.
"""

import pytest

from kalaana.redact import MASK, mask_names, safe_quote


@pytest.mark.parametrize(
    ("text", "masked"),
    [
        ("We need more officers like GP Bhavesh. Despite short staff", f"We need more officers like {MASK}. Despite short staff"),
        ("Rto officer Ketaki madam is the worst officer", f"Rto officer {MASK} madam is the worst officer"),
        ("Mrs Yamini was very helpful", f"Mrs {MASK} was very helpful"),
        ("an agent named Farhan openly sits alongside", f"an agent named {MASK} openly sits alongside"),
        ("One of the agents named Advait Rupal charged me Rs 9000", f"One of the agents named {MASK} charged me Rs 9000"),
        ("I reached out to Mr.Tanvir over phone", f"I reached out to Mr.{MASK} over phone"),
        ("RTO Tanvir and his team were prompt", f"RTO {MASK} and his team were prompt"),
        ("thanks to RTO officer K. L. Bhavesh for processing", f"thanks to RTO officer {MASK} for processing"),
        ("Ishaan sir helped me a lot", f"{MASK} sir helped me a lot"),
        ("named as Ishaan and Jatin!", f"named as {MASK} and {MASK}!"),
        ("RO Siddhant doesn't receive call", f"RO {MASK} doesn't receive call"),
        ("Shree. GP Bhavesh Regional Transport Officer", f"Shree. {MASK} Regional Transport Officer"),
        ("Rgds, Gaurang Mrinal", f"Rgds, {MASK}"),
        ("I think Name is Ujjwal (with glasses)", f"I think Name is {MASK} (with glasses)"),
        ("Mr.EHSAN was helpful", f"Mr.{MASK} was helpful"),
        ('named " TANVIR " sits outside', f'named " {MASK} " sits outside'),
        ("AGENT ZUBIN FULL FRAUD", f"AGENT {MASK} FULL FRAUD"),
        ("Agent named Ojas  Meher took 2000", f"Agent named {MASK} took 2000"),
        ("Mrs  Yamini", f"Mrs  {MASK}"),
        ("@Aarav helped", f"@{MASK} helped"),
        ("Dont go with Agent named ZubinKabir.", f"Dont go with Agent named {MASK}."),
        ("On PhonePe it showed the name QUAZI R. He took my RC", f"On PhonePe it showed the name {MASK} He took my RC"),
        ("approach Superident Yamini who is helpful", f"approach Superident {MASK} who is helpful"),
        ("Kudos to Jatin in F3 room", f"Kudos to {MASK} in F3 room"),
        ("They introduced me to Rehaan agent( his office is behind", f"They introduced me to {MASK} agent( his office is behind"),
        ("Transport officer Mr tanvir was helpful again", f"Transport officer Mr {MASK} was helpful again"),
        ("agent Pranit Charu Hridya Saanvi took 5000", f"agent {MASK} took 5000"),
    ],
)
def test_names_are_masked(text: str, masked: str) -> None:
    assert mask_names(text) == masked


@pytest.mark.parametrize(
    "text",
    [
        "The RTO Office in Electronic City is good. Thank you Sir",
        "Visited RTO South for my LL. Officers were helpful.",
        "Went to Room No. 3 on the first floor",
        "RTO Only money",
        "Wait starts for RTO Official",
        "go there like Bike owners do",
        "if you miss Anything, come back",
        "Bypassed agent, who said it takes 2 days",
        "WORKS ONLY THROUGH BROKER.",
        "Whithout agent they don't move",
        "get from a shop near RTO\n\nAll above docs should be attested",
        "write the name\nPhone number and address",
        "Thanks to God and the RTO team",
        "I went to Room No. 5 (classic RTO GPS error)",
        "Mr and Mrs came together",
        "Standard reply from the staff 'SERVER DOWN'! Pay bribe",
    ],
)
def test_ordinary_words_are_left_alone(text: str) -> None:
    assert mask_names(text) == text


def test_place_names_can_be_kept() -> None:
    text = "RTO Yelahanka is spacious"
    assert mask_names(text) == f"RTO {MASK} is spacious"  # can't tell a place from a name on its own
    assert mask_names(text, keep=frozenset({"Yelahanka"})) == text


def test_names_found_by_a_person_are_masked_without_a_cue() -> None:
    text = "it's a group.Jatin/Kabir Devika. shop number 45"
    assert mask_names(text) == text  # no cue: patterns can't see these
    assert mask_names(text, names=frozenset({"Jatin", "Kabir Devika"})) == f"it's a group.{MASK}/{MASK}. shop number 45"
    assert mask_names("Jatindra helped", names=frozenset({"Jatin"})) == "Jatindra helped"  # whole words only


def test_the_local_names_list_is_read_and_never_committed(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from kalaana import redact

    names = tmp_path / "names-to-mask.txt"
    names.write_text("# found by reading the quotes\nJatin\n  # an indented comment\n\n", encoding="utf-8")
    monkeypatch.setattr(redact, "LOCAL_NAMES", names)
    redact.local_names.cache_clear()
    try:
        assert safe_quote("ask Jatin at counter 2") == f"ask {MASK} at counter 2"
        assert redact.local_names() == frozenset({"Jatin"})
    finally:
        redact.local_names.cache_clear()
    gitignore = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
    assert "data/private/" in gitignore.splitlines()


def test_vehicle_and_shop_numbers_are_masked() -> None:
    assert safe_quote("He keeps (KA 99 ZZ 1234 as screensaver") == "He keeps ([vehicle number] as screensaver"
    assert safe_quote("my KA05AB1234 and KA-03-M-0001") == "my [vehicle number] and [vehicle number]"
    assert safe_quote("my new car 22 BH 1234 AB") == "my new car [vehicle number]"
    assert safe_quote("Agent shop No 45, from stall #30 and shop no 17") == (
        "Agent shop No [number], from stall #[number] and shop no [number]")
    kept = "KA-05 is in Anjanapura; get a copy at a near by shop\n4. Insurance copy; Room No. 5"
    assert safe_quote(kept) == kept  # office codes, list numbers and room numbers stay


def test_mobiles_are_masked_and_landlines_kept() -> None:
    quote = safe_quote("Agent Farhan gave 9845012345; office line 080 2663 0989")
    assert quote == f"Agent {MASK} gave 98••• •••45; office line 080 2663 0989"


def test_a_mobile_written_several_ways_is_masked_every_time() -> None:
    quote = safe_quote("call 9845012345 or 98450 12345, whatsapp +91 98450 12345, helpline 1800 258 1800")
    assert quote == "call 98••• •••45 or 98••• •••45, whatsapp 98••• •••45, helpline 1800 258 1800"


def test_ai_text_masks_only_listed_names_not_ordinary_words() -> None:
    from kalaana.redact import mask_listed
    text = "Senior Sub Registrar: Ganesh N (Mobile). Official Website: RTO Code KA-05."
    assert mask_listed(text, frozenset({"Ganesh N"})) == "Senior Sub Registrar: [name] (Mobile). Official Website: RTO Code KA-05."
