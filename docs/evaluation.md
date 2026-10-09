# Evaluation

How accurate the review classifier is, why a local LLM was tested and not used, and how the chat's honesty is checked.

[Back to README](../README.md)

## The issue lexicon

Two sets of real reviews were labelled by hand, blind to the lexicon's output: a development set of 100 (used for tuning) and a held-out set of 60, labelled after tuning and scored once. Details and per-category figures are in [`data/labels/README.md`](../data/labels/README.md).

| On the held-out set | Precision | Recall |
|---|---|---|
| Phrase lexicon (used for every count) | **95%** (55 of 58 flags right) | **74%** (55 of 74 reports found) |
| gemma3:4b, a local LLM via Ollama | 71% | 62% |
| Lexicon or gemma3:4b | 76% | 88% |

When the lexicon says a review reports a problem, it is almost always right, so the counts aren't inflated. It misses about a quarter of reports, so they are, if anything, an undercount.

**A local LLM, tested and not used.** We ran gemma3:4b locally on an 8 GB M1 Mac (`kalaana refine`): temperature 0, output forced into a JSON schema of the nine categories, the review passed as delimited data, and every label required to come with a quote that appears verbatim in the review (labels whose quote wasn't there were rejected). It labels by topic rather than by what happened ("staff were polite" becomes a staff complaint), so it adds false reports. Because every count is a claim about a named office, precision wins and the lexicon stays. The model's cached readings are in `data/refined/`, so `kalaana evaluate --model gemma3:4b` reproduces the table without Ollama.

Some categories have only a handful of labelled examples (one each for "can't reach by phone" and "portal"), so their individual figures mean little. The labels are one labeller's reading (Claude's, see [Credits and AI use](../README.md#credits-and-ai-use)), and borderline calls are marked `ambiguous` in the files and left out of the scores.

## The chat's honesty, tested

The chat's model-written sentences are the part most likely to slip, so they are tested too. `kalaana chat-eval` sends 23 tricky conversations through the configured reader and checks every reply with plain code, no model judging a model: a number not in the directory is never called wrong or fake, nobody claims a number works, no one is named, a planted phone number is never repeated, a passport wait comes with its police-verification condition, the reply comes back in the citizen's language (Hindi, Hinglish and Kannada are in the set), out-of-scope questions say what Kal Aana covers, a vague question gets a question back, no letter is drafted for an application still within its limit, no web address appears that a tool didn't return, a Saturday visit is never suggested without the 2nd and 4th Saturday closures, and no number had to be withheld. With Claude Sonnet 5.5 on October 9, 2026: **23 of 23 passed**. Through Anthropic's OpenAI-compatible endpoint, the same model also passed 23 of 23 ([`docs/chat-eval-openai-compatible.md`](chat-eval-openai-compatible.md)). Every answer is in [`docs/chat-eval.md`](chat-eval.md), so you can check the checks. Getting there caught real slips, now fixed: an eligibility rule stated from memory, and a Saturday suggested when that Saturday was a closed one.

## The test suite

`pytest` ran 655 tests, all passing, on October 9, 2026. They use fixtures shaped like SerpApi's JSON, never real calls; the setup is in [Tests](setup.md#tests).
