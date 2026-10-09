# Labelled reviews for evaluating the issue lexicon

Two sets of real Google Maps reviews of Bengaluru RTOs, drawn at random with fixed seeds from
the collection of Oct 8, 2026. Each mixes reviews from the newest-first samples
(representative of recent reviews) with reviews from the keyword-filtered samples (rich in the
rarer problems, so recall can be measured). Reviewer names and profiles are not stored.

| File | Reviews | Seed | Used for |
|---|---|---|---|
| `rto-reviews.jsonl` | 100 (60 newest, 40 keyword) | 2026 | development: its errors were studied and the lexicon tuned on them |
| `rto-reviews-heldout.jsonl` | 60 (36 newest, 24 keyword), none from the first set | 2027 | the reported accuracy: labelled blind after tuning, evaluated once, never tuned on |

Each review was labelled by reading its text only, without looking at the lexicon's output.
`labels` lists every category the review reports; `ambiguous` names categories a reasonable
reader could label either way, with the reason in `note`. Ambiguous categories are left out
of the precision and recall figures and listed for the owner to check.

## What each label means

A review gets a label when the reviewer reports it about this office, from their own
experience or as a plain statement of fact. Denials ("I didn't have to pay any bribe"),
hypotheticals and advice about other offices don't count.

| Label | The reviewer reports... |
|---|---|
| unreachable | failing to reach the office by phone: the number doesn't work, nobody answers, calls or emails go unanswered |
| bribe | a bribe or unofficial payment demanded or paid at this office, or corruption here stated as fact |
| tout | agents, brokers or middlemen involved in getting work done here: used, pushed towards, operating inside, or given priority |
| delay | waiting longer than expected for an outcome: an application pending for days, weeks or months, a document not received |
| staff | staff who are rude, absent from their seats, unhelpful, careless or incompetent |
| portal | the online system, server or website failing |
| closed | the office closed or shut when it should be open, staff away during office hours, hours not kept |
| queue | long queues, hours of waiting in the office, or heavy crowding |
| helpful | praise for helpful staff or quick, smooth service here (not sarcasm) |

## Results (lexicon only, ambiguous labels excluded)

Run `python -m kalaana evaluate`. On the held-out set:

| | Reviews with the label | Precision | Recall |
|---|---|---|---|
| unreachable | 1 | 100% | 100% |
| bribe | 16 | 100% | 75% |
| tout | 15 | 100% | 93% |
| delay | 4 | 60% | 75% |
| staff | 17 | 92% | 71% |
| portal | 1 | n/a | 0% |
| closed | 4 | 100% | 50% |
| queue | 7 | 100% | 57% |
| helpful | 9 | 100% | 78% |
| **all categories** | 74 | **95%** (55 of 58 flags right) | **74%** (55 of 74 reports found) |

On the development set, the first blind run (before tuning) was 86% precision and 66% recall.
After tuning it reads 91% and 87%, which overstates real accuracy, so it is not reported.

What this means: when the lexicon says a review reports a problem, it is almost always right,
so the shares in the report card are not inflated. It misses about a quarter of reports,
mostly complaints about staff, queues and closures phrased in ways no pattern anticipates,
so the shares are, if anything, an undercount. Several categories have only a handful of
labelled examples, so their individual figures are rough.

The labels are one labeller's (Claude's) reading. Every `ambiguous` call is listed in the file
for the owner to check.

## A local LLM, tested and not used for the counts

We also asked a small local model to read the same reviews (`python -m kalaana refine`, Ollama, gemma3:4b on an M1 Mac with 8 GB, temperature 0, answers forced into a JSON schema of the nine categories, every label backed by a quote that must appear verbatim in the review). The prompt was tuned on the development set only, then scored once on the held-out set:

| Setup | Precision | Recall |
|---|---|---|
| Phrase lexicon (used on the site) | 95% | 74% |
| gemma3:4b alone | 71% | 62% |
| Lexicon or gemma3:4b | 76% | 88% |

The model labels by topic more than by what happened ("staff were polite" read as a staff complaint), so it adds false reports. Because every count on the site is a claim about an office, precision matters more than recall, and the lexicon stays. The model's readings are cached in `data/refined/gemma3-4b.jsonl`. Qwen 3.5 4B (including its MLX build) was tried first, but Ollama 0.40 doesn't support structured output for it.
