# Limitations, ethics and data notice

What the data can't tell you, how people are protected, and the terms under which the captured data is published.

[Back to README](../README.md)

## Limitations

- **Reviews are self-selected.** People with a bad experience write more of them. Counts are shown with their denominator and date range, never as a rate for the office.
- **Samples are small.** Google's newest-first paging stops after about 25 reviews on some listings. 8 of 13 RTOs and 15 of 42 sub-registrar listings have 10 or more recent reviews with text; the rest say "too few reviews".
- **The lexicon was measured on RTO reviews only.** Its 95% precision comes from hand-labelled RTO reviews; on sub-registrar reviews it is untested, so treat those counts as indicative.
- **AI answers change** with the query and the day. The AI Overviews and AI Mode answers shown are what Google returned on October 8, 2026, for the exact query shown, with the search ID.
- **Bing matching is by location.** A Bing place counts as the office only within 400 m of its Google listing (or by name when Google has none), so offices we couldn't match say so rather than "no listing".
- **Matching can miss duplicates.** "People also search for" panels show listings our sweep didn't return. KA-59 and the BDA sub-registrar office weren't found at all, which is not proof they have no listing. Some matches rest on location alone (the same PIN or place name); the office card says so.
- **Directories go out of date.** The sub-registrar directory lists one office mobile number per office, which can change when officers move. "Not in the directory" means exactly that, not that a number is wrong.
- **Name masking is pattern-based.** It catches names next to a cue (Mr, officer, madam, "named", "kudos to"). Every committed quote was also read in full by a separate AI reviewer (Claude, in a fresh session) looking for names and identifiers. Names found that way are masked through a local list that is never committed, because a list of names is exactly what must not be published.
- **Facilities complaints** (cleanliness, parking, washrooms) aren't counted, because no statutory promise covers them.
- **Tamil and Telugu** patterns are tested but unmeasured on real text: in our RTO collection (not committed), only 5 of the 438 reviews with text are in Indian scripts.
- **One city so far.** All three office types are Bengaluru's; another city needs its own directories and searches (see [Another city](serpapi.md#another-city)), and the web app shows one city at a time.

## Ethics

- **Offices, not individuals.** No staff member or private individual is named anywhere. (Businesses appear only by the names on their own Google listings, for example listings named like a passport office.) Names, mobile numbers that aren't in an official directory, vehicle registrations and agents' shop numbers are masked in every quote. Officers' official numbers stay visible because they are the published public contact points.
- **No reviewer identities.** No reviewer's name or profile is in any committed file or shown anywhere; the committed snapshot and labelled sets hold masked text only. (The raw search cache, which is never committed, holds SerpApi's responses as received.)
- **No record of conversations.** The chat keeps no record on the server; the conversation lives in the visitor's browser tab. With a model reader, messages go to that model's API, and a live search sends a short query to SerpApi; live results are cached for an hour, then deleted.
- **Careful wording.** "Reviewers report", "possible breach" and "listing score", never "this office is corrupt".
- **Nothing is sent on anyone's behalf.** The complaint letter is a draft the citizen reads, edits and sends.
- **Untrusted text stays data.** Review text never reaches a model as instructions, and the MCP tools label quotes as data.

## Data and content notice

The snapshots in `data/snapshot/` are a dated research capture (October 8, 2026) made through SerpApi, for citizen information and public-interest research. Review quotes are short, masked excerpts that belong to their authors and Google, and each links to the original. Google's AI Overview and AI Mode text is shown as captured, with unverified mobile numbers, emails and listed names masked. Official contact details and time limits come from the departments' own published directories and the Sakala Service Compendium (May 5, 2026), retrieved October 8, 2026, with each source linked in `data/official/`. If you are named or quoted and want something removed, open an issue on this repository.
