"""What citizens report about a public office: an explainable, multilingual issue lexicon.

Each category is a list of patterns tagged with a language. A match keeps its exact span, so
the evidence shown is always the reviewer's own words, never a paraphrase. Languages: English
(en), Kannada (kn), Hindi (hi), Tamil (ta) and Telugu (te) in their own scripts, plus Kannada
and Hindi typed in Latin letters (kn-latn, hi-latn), which is how many reviews are written.

The lexicon is deliberately conservative: a pattern is a phrase someone reporting the problem
would use, not a loose keyword. Denials ("didn't have to pay any bribe") are not reports.
Precision and recall are measured on hand-labelled real reviews (see the evaluation), not
assumed. Only a handful of the collected reviews are in Indian scripts, so the non-English
patterns are tested here but not yet measured on real text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

Polarity = Literal["problem", "positive"]
Language = Literal["en", "kn", "hi", "ta", "te", "kn-latn", "hi-latn"]
Source = Literal["text", "original"]


@dataclass(frozen=True)
class Pattern:
    language: Language
    regex: str


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    polarity: Polarity
    patterns: tuple[Pattern, ...]
    # Text anywhere in the same sentence that makes a match information, not a report
    # (e.g. "closed on the 2nd and 4th Saturday" is the official holiday rule).
    exceptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Hit:
    category: str
    language: Language
    start: int  # offsets into the string named by `source`
    end: int
    text: str  # the matched words, verbatim
    source: Source = "text"  # "original": the reviewer's own words; "text": Google's English (or the same)


def P(language: Language, regex: str) -> Pattern:
    return Pattern(language, regex)


_N2PLUS: Final = r"(?:[2-9]|[1-9]\d|two|three|four|five|six|seven|eight|nine|ten)"  # 2 hours or more

CATEGORIES: Final = (
    Category("unreachable", "Can't reach them by phone", "problem", (
        P("en", r"\b(?:no\s?one|nobody|none)\s+(?:ever\s+)?(?:picks?|picked|lifts?|lifted|answers?|answered|attends?|receives?)(?:\s+up)?(?:\s+the)?\s+(?:phones?|calls?)\b"),
        P("en", r"\b(?:no\s?one|nobody|none)\s+(?:ever\s+)?(?:picks?|picked|answers?|answered)(?:\s+up)?\b"),
        P("en", r"\b(?:don'?t|doesn'?t|do\s+not|does\s+not|never|won'?t|didn'?t|not)\s+(?:even\s+)?(?:pick|attend|take|receive|answer|lift)\w*(?:\s+up)?[^.!?]{0,20}?\b(?:calls?|phones?)\b"),
        P("en", r"\b(?:phone(?!\s*pay)|land\s?line|telephone|helpline|contact)(?:\s+numbers?|s)?\b[^.!?]{0,40}?\b(?:not\s+(?:working|reachable|answered|picked|connecting)|out\s+of\s+(?:order|service)|dead|unreachable|switched\s+off|switch\s+off|never\s+answered|doesn'?t\s+work|does\s+not\s+work|always\s+(?:says\s+)?busy|useless)\b"),
        P("en", r"\bcalls?\s+(?:are\s+|is\s+|were\s+)?(?:not|never)\s+(?:answered|picked|received|attended|connected)\b"),
        P("en", r"\b(?:can\s?not|can'?t|couldn'?t|could\s+not|unable\s+to|impossible\s+to)\s+(?:reach|contact|get\s+through\s+to|connect\s+(?:to|with))\b[^.!?]{0,30}?\b(?:phone|calls?|them|office|rto|anyone)\b"),
        P("en", r"\b(?:phone|call|email|e-mail|mail)\w*\b[^.!?]{0,30}?\bno\s+(?:reply|response|answer)\b"),
        P("en", r"\bnot\s+reachable\b|\balways?\s+(?:says\s+)?busy\b"),
        P("en", r"\b(?:contact|phone)\s+numbers?\b[^.!?]{0,25}?\b(?:is|are|was)\s+(?:fake|wrong|incorrect|a\s+scam)\b"),
        P("en", r"\btrying\s+to\s+(?:reach|call|contact)\b[^.!?]{0,40}?\b(?:busy|no\s+(?:answer|response|reply)|not\s+(?:answered|picked|reachable))\b"),
        P("kn-latn", r"\bphone\s+(?:receive\s+|recieve\s+|pick\s+)?(?:madalla|maadalla|madolla|maadolla|tegeyalla|tegiyalla|ettalla|ettolla|ethalla|ettodilla)\b"),
        P("kn", r"ಫೋನ್[^.!?]{0,20}?(?:ಸ್ವೀಕರಿಸು|ತೆಗೆಯು|ಎತ್ತು|ರಿಸೀವ್)\S*(?:ದಿಲ್ಲ|ಲ್ಲ)"),
        P("kn", r"ಸಂಪರ್ಕ(?:ಕ್ಕೆ)?\s+ಸಿಗು(?:ತ್ತಿಲ್ಲ|ವುದಿಲ್ಲ)"),
        P("hi", r"फ़?ोन[^।.!?]{0,20}?\s(?:नहीं|नही)\s+(?:उठा|लग|मिल)"),
        P("hi-latn", r"\bphone\s+(?:kabhi\s+)?(?:nahi|nahin|nai)\s+(?:utha|uthate|uthata|lagta|lagra|lag\s+raha|milta)\w*"),
        P("ta", r"(?:போன்|தொலைபேசி)[^.!?]{0,20}?(?:எடுக்க|பதில்)[^.!?]{0,10}?(?:இல்லை|மாட்டா)"),
        P("te", r"ఫోన్[^.!?]{0,20}?(?:ఎత్త|తీయ)\S*\s*(?:లేదు|రు\b)"),
    )),
    Category("bribe", "Bribe demanded or paid", "problem", (
        P("en", r"\bbrib(?:e|es|ed|ery|ing)\b"),
        P("en", r"\bcorrupt(?:ion|ed)?\b"),
        P("en", r"\bno\s+money,?\s+no\s+work\b|\bextra\s+(?:money|amount|cash|payment)\b|\bunder\s+the\s+table\b|\bspeed\s+money\b|\bkick\s?backs?\b"),
        P("en", r"\b(?:demand(?:ed|s|ing)?|ask(?:ed|s|ing)?\s+for)\s+(?:(?:rs\.?|₹|inr|rupees)\s?\d[\d,]*|\d[\d,]*\s?(?:rs\b|₹|rupees|/-)|\d{3,}\b)"),
        P("en", r"\bmoney[- ]minded\b|\b(?:chai|tea)[- ](?:pani|and\s+coffee|money)\b"),
        P("en", r"\bcommission\s+(?:goes|go|went|is\s+shared)\s+to\b|\bcurrency\s+(?:kept|placed|put)\s+in\b"),
        P("en", r"\bcollect(?:ing|ed|s)?\s+(?:rs\.?\s?|₹\s?)?\d+(?:\s*[,/]\s*\d+)*\b[^.!?]{0,30}?\b(?:already\s+paid|extra|for\s+nothing)\b"),
        P("kn", r"ಲಂಚ(?!್)"),
        P("kn-latn", r"\blancha\w*"),
        P("hi", r"रिश्वत|घूस"),
        P("hi-latn", r"\b(?:rishwat|ghoos|chai[- ]?pani)\b"),
        P("ta", r"லஞ்ச"),
        P("te", r"లంచ"),
    )),
    Category("tout", "Agents or brokers involved", "problem", (
        P("en", r"\b(?:agents?|brokers?|middle\s?m[ae]n|touts?|dalals?|mediators?)\b"),
        P("en", r"\bthrough\s+(?:a\s+|the\s+)?driving\s+schools?\b|\bdriving\s+school\s+(?:people|agents?|guys)\b"),
        P("en", r"\b(?:delegated|left|outsourced)\s+to\s+(?:the\s+)?driving\s+schools?\b|\b(?:come|go|sent|send|ask\w*\s+(?:you\s+)?(?:to\s+)?come)\s+(?:to\s+|through\s+)?(?:a\s+|the\s+)?private\s+driving\s+(?:schools?|institut\w*)"),
        P("kn", r"ಮಧ್ಯವರ್ತಿ|ದಲ್ಲಾಳಿ|ಏಜೆಂಟ(?:್|ರು)|ಬ್ರೋಕರ್"),
        P("kn-latn", r"\b(?:madhyavarthi|madhyavarti|dallali)\w*"),
        P("hi", r"दलाल|एजेंट|बिचौलि"),
        P("hi-latn", r"\b(?:dalal|bichauliya|bicholiya)\w*"),
        P("ta", r"இடைத்தரகர்|புரோக்கர்|ஏஜெ[ன்ண]்ட்"),
        P("te", r"దళారీ|బ్రోకర్|ఏజెంట్"),
    )),
    Category("delay", "Waits beyond the promised time", "problem", (
        P("en", r"\b(?:pending|waiting|not\s+(?:yet\s+)?(?:received|approved|issued|processed|done|delivered)|no\s+(?:progress|update|response)|still\s+(?:not|waiting|pending))\b[^.!?]{0,60}?\b(?:\d+|one|two|three|four|five|six|several|many)\s*(?:days?|weeks?|months?|years?)\b"),
        P("en", r"\b(?:\d+|one|two|three|four|five|six|several|many)\s*(?:days?|weeks?|months?)\b[^.!?]{0,40}?\b(?:over|passed|gone|later|since|and\s+still|still|no\s+(?:progress|update|response)|not\s+(?:yet\s+)?(?:received|approved|issued|got))\b"),
        P("en", r"\b(?:it'?s|it\s+has|has)\s+been\s+(?:more\s+than\s+|over\s+|almost\s+|nearly\s+)?(?:\d+|a|one|two|three|four|five|six|several|many)\s*(?:days?|weeks?|months?|years?)\b"),
        P("en", r"\b(?:more\s+than|over|almost|nearly)\s+(?:a\s+|\d+\s+|one\s+|two\s+|three\s+)?(?:days?|weeks?|months?|year)\b"),
        P("en", r"\b(?:stuck|pending|waited|waiting)\b[^.!?]{0,30}?\b(?:for\s+)?(?:\d+(?:\.\d)?|several|many|few)\s*(?:days?|weeks?|months?)\b"),
        P("en", r"\b(?:takes?|will\s+take)\s+(?:at\s*least\s+|atleast\s+|about\s+|around\s+|almost\s+)?(?:(?:\d+(?:\.\d)?|a|one|two|three|several)\s*(?:weeks?|months?)|(?:[1-9]\d|\d{3})\s*days?)\b"),
        P("en", r"\b(?:\d+|a|one|two|three|several)\s*(?:weeks?|months?)\s+ago\b[^.!?]{0,40}?\bnot\s+(?:even\s+)?(?:started|done|received|processed|approved)\b|\bafter\s+(?:\d+|several)\s+months?\s+of\s+(?:application|applying)\b"),
        P("en", r"\btook\s+(?:me\s+|us\s+|them\s+)?(?:about\s+|around\s+|almost\s+|over\s+|more\s+than\s+|nearly\s+)?(?:(?:\d+|a|one|two|three|four|five|six|several)\s*(?:weeks?|months?)|(?:[1-9]\d|\d{3})\s*days?)\b"),
        P("en", r"\bno\s+progress\b|\bstill\s+(?:not\s+(?:yet\s+)?(?:received|approved|issued)|pending|waiting)\b|\b(?:not\s+yet|yet\s+to)\s+(?:got|get|receive|received|be\s+(?:approved|issued))\b|\bdelay(?:ed|s)?\b"),
        P("kn", r"ವಿಳಂಬ|ತಡವಾಗಿ|ಇನ್ನೂ\s+(?:ಬಂದಿಲ್ಲ|ಸಿಕ್ಕಿಲ್ಲ|ಅನುಮೋದ)"),
        P("hi", r"देरी|देर\s+से|अभी\s+तक\s+नहीं"),
        P("hi-latn", r"\b(?:abhi\s+tak\s+nahi|deri)\b"),
        P("ta", r"தாமத"),
        P("te", r"ఆలస్య"),
    )),
    Category("staff", "Staff absent, rude or unhelpful", "problem", (
        P("en", r"\b(?:rude(?:ly|ness)?|arrogan(?:t|ce)|misbehav\w*|shout(?:s|ed|ing)?|lazy|careless|irresponsible|incompeten(?:t|ce)|inept|harass\w*|unhelpful|nonsense\s+(?:employees|staff|officers|people))\b"),
        P("en", r"\b(?:bad|worst|more|rude|arrogant|government\s+job)\s+attitude\b|\battitude\s+(?:problem|issue)s?\b"),
        P("en", r"\b(?:no\s?one|nobody|none)(?:\s+is)?(?:\s+there)?\s+(?:to\s+)?(?:guide|guides|respond|responds|help|helps)\b"),
        P("en", r"\b(?:not|never)\s+(?:responding|guiding|helping|cooperating|in\s+(?:their\s+)?seats?)\b|\bdon'?t\s+(?:guide|care|respond|help)\b"),
        P("en", r"\bbad\s+(?:behaviou?r|behavier)\b|\bbehaved?\s+(?:extremely\s+|very\s+)?(?:bad|badly|rudely)\b|\bpass(?:es)?\s+(?:you\s+|people\s+)?from\s+one\s+(?:counter|table|desk)\s+to\s+another\b"),
        P("en", r"\bwaste\s+(?:everyone'?s\s+|our\s+|your\s+|my\s+|people'?s\s+)?time\b"),
        P("en", r"\b(?:worst|slowest|shameless|useless|lazy|corrupt)\s+(?:\w+\s+)?(?:officers?|officials?|employees|staff|people)\b|\bemployees\s+(?:don'?t|do\s+not)\s+want\s+to\s+work\b"),
        P("en", r"\b(?:run|running|move|moving|roam\w*)\s+(?:from\s+)?(?:pill[ae]r\s+to\s+post|door\s+to\s+door|desk\s+to\s+desk|counter\s+to\s+counter)\b"),
        P("en", r"\b(?:won'?t|don'?t|do\s+not|will\s+not)\s+give\s+(?:you\s+)?(?:proper|correct|any)\s+information\b|\bnot\s+responding\s+properly\b|\bunprofessional\b|\bhardly\s+(?:you\s+)?find\s+(?:the\s+)?staff\b"),
        P("kn", r"ಅಸಭ್ಯ|ಉದ್ಧಟ|ಸಿಬ್ಬಂದಿ\s+ಇಲ್ಲ|ಸರಿಯಾಗಿ\s+ಮಾತನಾಡ(?:ುವುದಿಲ್ಲ|ಲ್ಲ|ಲಿಲ್ಲ)"),
        P("hi", r"बदतमीज़?|बेरुखी|लापरवाह"),
        P("hi-latn", r"\b(?:badtameez|laparwah)\w*"),
        P("ta", r"திமிர்|அலட்சிய"),
        P("te", r"నిర్లక్ష్య|దురుసు"),
    )),
    Category("portal", "Portal, server or website failures", "problem", (
        P("en", r"\bservers?\s+(?:is\s+|was\s+|are\s+)?(?:down|slow|not\s+working|issue|problem|error)\b"),
        P("en", r"\b(?:website|portal|site|online\s+system|parivahan|sarathi|vahan|software)\b[^!?]{0,60}?\b(?:not\s+working|down|error|glitch\w*|crash\w*|fail\w*|issue|problem|bug)\b"),
        P("en", r"\b(?:glitch\w*|technical\s+(?:issue|problem|error)s?|otp\s+(?:not|never)\s+(?:received|coming|came))\b"),
        P("kn", r"ಸರ್ವರ್\s+(?:ಡೌನ್|ಸಮಸ್ಯೆ)|ವೆಬ್‌?ಸೈಟ್[^.!?]{0,20}?ಕೆಲಸ\s+ಮಾಡು(?:ತ್ತಿಲ್ಲ|ವುದಿಲ್ಲ)"),
        P("hi", r"सर्वर\s+(?:डाउन|बंद|खराब)|साइट\s+(?:नहीं\s+चल|बंद)"),
        P("hi-latn", r"\bserver\s+(?:band|kharab)\b"),
    ), exceptions=(
        r"\b(?:phone|contact|helpline)?\s*numbers?\s+(?:mentioned|given|listed|shown|provided)\s+(?:on|in)\s+(?:the\s+)?(?:website|site|portal)",
    )),
    Category("closed", "Closed or not keeping its hours", "problem", (
        P("en", r"\b(?:office|rto|counters?|operations?|they)\s+(?:was\s+|is\s+|were\s+|are\s+)?(?:completely\s+|fully\s+)?(?:closed|shut(?:\s+down)?)\b"),
        P("en", r"\bnot\s+(?:open|opened)\s+(?:on\s+time|at)\b|\b(?:no\s?one|nobody)\s+(?:was\s+|is\s+)?(?:there|present|available)\b"),
        P("en", r"\blunch\s+(?:break|time)\b[^.!?]{0,30}?\b(?:till|until|upto|up\s+to)\b"),
        P("en", r"\b(?:assigned|deputed|pulled|sent|diverted)\b[^.!?]{0,30}?\b(?:election|sir|survey|census)(?:\s*\([^)]{0,40}\))?\s+duty\b|\bnot\s+(?:maintain|follow|keep)(?:ing)?\s+(?:proper\s+)?timings?\b"),
        P("en", r"\b(?:due\s+to|on|for)\s+(?:election|sir|survey|census)(?:\s*\([^)]{0,40}\))?\s+duty\b"),
        P("kn", r"ಮುಚ್ಚ(?:ಲಾಗಿದೆ|ಿದ್ದ|ಿತ್ತು)|ಬಂದ್"),
        P("hi", r"बंद\s+(?:था|है|रहता|मिला)"),
        P("hi-latn", r"\b(?:band\s+tha|band\s+hai|band\s+rehta)\b"),
    ), exceptions=(
        # Karnataka government offices close on the 2nd and 4th Saturday, Sundays and holidays by rule.
        r"\b(?:2nd|second|4th|fourth)\b[^.!?]{0,25}?\bsaturdays?\b",
        r"\b(?:sundays?|public\s+holidays?|government\s+holidays?|gazetted\s+holidays?)\b",
        r"ಎರಡನೇ[^.!?]{0,25}?ಶನಿವಾರ|दूसरे[^।.!?]{0,25}?शनिवार",
        r"(?:सर्वर|साइट|server|site|website|portal)\s*(?:is\s+|was\s+)?(?:बंद|band)",
    )),
    Category("queue", "Long queues and waiting", "problem", (
        P("en", r"\b(?:long|huge|big|endless|multiple|\d+(?:-\d+)?)\s+(?:queues?|lines?)\b|\bstand(?:ing)?\s+in\s+(?:the\s+)?(?:queue|line)\s+for\s+(?:a\s+)?(?:long|hours)\b"),
        P("en", rf"\b(?:waited|waiting|wait(?:ed)?\s+for|stood|standing|spent|wasted)\s+(?:for\s+)?(?:about\s+|around\s+|almost\s+|over\s+|more\s+than\s+|nearly\s+)?{_N2PLUS}(?:\.\d)?\s*(?:-|to)?\s*(?:\d+)?\s*(?:hours?|hrs?)\b"),
        P("en", rf"\btook\s+(?:me\s+|us\s+)?(?:about\s+|around\s+|almost\s+|over\s+|more\s+than\s+|nearly\s+)?{_N2PLUS}\s*(?:-|to)?\s*(?:\d+)?\s*(?:hours?|hrs?)\b"),
        P("en", r"\b(?:half|whole|entire|full)\s+day\b[^.!?]{0,30}?\b(?:queue|line|wait\w*|wasted)\b"),
        P("en", r"\b(?:very|too|so|always|usually|heavily|extremely)\s+(?:over)?crowded\b|\bhuge\s+crowd\b"),
        P("kn", r"ಸರತಿ|ಕ್ಯೂ"),
        P("hi", r"लंबी\s+(?:लाइन|कतार)|कतार"),
        P("hi-latn", r"\blambi\s+line\b"),
        P("ta", r"வரிசை(?!\s*எண்)"),
        P("te", r"క్యూ|వరుసలో"),
    )),
    Category("helpful", "Helpful, quick service", "positive", (
        P("en", r"(?<!un)(?<!un-)(?<!citizen )(?<!citizen-)\b(?:very\s+|really\s+|super\s+|extremely\s+)?(?:helpful|polite|courteous|cooperative|co-operative|supportive|friendly|humble|prompt|efficient|smooth|seamless|hassle[- ]free|well[- ]organi[sz]ed)\b"),
        P("en", r"\b(?:quick(?:ly)?|fast|swift(?:ly)?)\b[^.!?]{0,20}?\b(?:service|process\w*|done|approved|work)\b|\bdone\s+in\s+(?:less\s+than\s+)?(?:\d+|a\s+few|few)\s+(?:min|minutes?|hours?)\b"),
        P("en", r"\bgood\s+(?:experience|service)\b|\bexcellent\b|\bthank\s+you\b|\bthanks\b(?!\s+(?:to|for\s+the\s+corruption))"),
        P("kn", r"ಸಹಾಯ\s+ಮಾಡಿದ(?:ರು|್ರು)|ಉತ್ತಮ\s+ಸೇವೆ|ಒಳ್ಳೆಯ\s+ಸೇವೆ|ಧನ್ಯವಾದ"),
        P("kn-latn", r"\b(?:olle\s+seve|chennagi\s+help)\w*"),
        P("hi", r"मददगार|अच्छी\s+सेवा|धन्यवाद"),
        P("hi-latn", r"\b(?:achhi\s+seva|madadgar)\b"),
        P("ta", r"நல்ல\s+சேவை|உதவி\s+செய்"),
        P("te", r"మంచి\s+సేవ|సహాయం\s+చేశ"),
    )),
)

BY_ID: Final = {c.id: c for c in CATEGORIES}
_COMPILED: Final = tuple((c.id, p.language, re.compile(p.regex, re.I)) for c in CATEGORIES for p in c.patterns)
_EXCEPTIONS: Final = {c.id: tuple(re.compile(e, re.I) for e in c.exceptions) for c in CATEGORIES}

# --- Denials ---------------------------------------------------------------------------------
# English: a negative among the last few words of the same clause before the match denies it
# ("didn't have to pay any bribe", "never felt the need for an agent", "none of them are helpful").
_CLAUSE_BREAK: Final = re.compile(r"[,.;:!?\n]|\bbut\b", re.I)
_NEGATIVE: Final = re.compile(
    r"\b(?:no|not|never|without|nobody|no\s?one|none|nothing|nowhere|zero|"
    r"didn'?t|did\s+not|don'?t|do\s+not|doesn'?t|does\s+not|wasn'?t|was\s+not|isn'?t|is\s+not|"
    r"aren'?t|are\s+not|weren'?t|were\s+not|haven'?t|have\s+not|hasn'?t|has\s+not|won'?t|will\s+not)\b", re.I)
NEGATION_WINDOW_WORDS: Final = 8
# ...unless the same sentence then says nothing gets done that way, which turns the denial into a
# claim: "without bribe nothing moves", "no application is accepted without middlemen".
_TURNS_INTO_CLAIM: Final = re.compile(
    r"\b(?:nothing\s+(?:works|moves|happens|will\s+(?:happen|move)|gets\s+done|is\s+done|done)|no\s+work|"
    r"no\s+application|not\s+possible|impossible|won'?t\s+(?:work|move|happen|do|process)|"
    r"will\s+not\s+(?:work|move|happen|do|process)|(?:can'?t|cannot)\s+get|"
    r"(?:they|he|she|officers?|officials?|staff)\s+(?:asked|demanded|wanted|expected))\b", re.I)
# "If I could have gone with an agent...": a hypothetical, not a report.
_HYPOTHETICAL: Final = re.compile(r"\bif\s+(?:i|you|we|one)\s+(?:could|would|had|have|go|went|had\s+gone)\b|\bmay\s*be\s+i\s+would\b", re.I)
# "Staff should be more helpful": a wish, not praise.
_WISH: Final = re.compile(r"\b(?:should|could|must|needs?\s+to|ought\s+to)\s+(?:be|have\s+been)(?:\s+(?:more|a\s+bit|little))?\s*$", re.I)
# "Never give your application to the agent outside": a warning that agents operate there.
_WARNING: Final = re.compile(r"^\s*(?:never|don'?t|do\s+not|dont)\s+(?:give|go|trust|approach|pay|hire|use|believe|fall|engage|entertain)\b", re.I)
# Other languages put the negative after the word ("ಲಂಚ ಕೊಡಬೇಕಾಗಿಲ್ಲ", "रिश्वत नहीं ली").
_NEGATIVE_AFTER: Final[dict[str, re.Pattern[str]]] = {
    "kn": re.compile(r"^\s*\S*\s*(?:ಕೊಡಬೇಕಾಗಿಲ್ಲ|ಕೊಡಲಿಲ್ಲ|ಕೇಳಲಿಲ್ಲ|ಕೇಳುವುದಿಲ್ಲ|ತೆಗೆದುಕೊಳ್ಳಲಿಲ್ಲ|ಇಲ್ಲ(?!ದೆ))"),
    "kn-latn": re.compile(r"^\s*(?:illa|kodbekilla|kodlilla|kelilla)\b", re.I),
    "hi": re.compile(r"^\s*(?:नहीं|नही)\s*(?:ली|लिया|लेते|दी|दिया|देनी|देना|मांग|माँग)"),
    "hi-latn": re.compile(r"^\s*(?:nahi|nahin|nai)\s+(?:li|liya|lete|di|diya|dena|mang\w*)\b", re.I),
    "ta": re.compile(r"^\s*\S*(?:இல்லை|வில்லை)"),
    "te": re.compile(r"^\s*\S*లేదు"),
}
# "बिना रिश्वत काम हो गया": done without a bribe.
_DONE_WITHOUT: Final = re.compile(r"बिना\s*$")
_GOT_DONE: Final = re.compile(r"^[^।.!?]{0,25}?(?:हो\s+गया|हो\s+गई|हुआ)")


def _sentence(text: str, start: int, end: int) -> tuple[int, int]:
    left = max(text.rfind(c, 0, start) for c in ".!?\n।") + 1
    rights = [i for i in (text.find(c, end) for c in ".!?\n।") if i != -1]
    return left, (min(rights) if rights else len(text))


def _negated(text: str, start: int, end: int, language: Language, category: str = "") -> bool:
    """True when the reviewer is denying the matched words rather than reporting them."""
    if language != "en":
        after = _NEGATIVE_AFTER.get(language)
        if after and after.search(text[end:end + 25]):
            return True
        return bool(_DONE_WITHOUT.search(text[max(0, start - 8):start]) and _GOT_DONE.search(text[end:]))
    breaks = list(_CLAUSE_BREAK.finditer(text, 0, start))
    clause = text[breaks[-1].end() if breaks else 0:start]
    window = " ".join(clause.split()[-NEGATION_WINDOW_WORDS:])
    if _HYPOTHETICAL.search(window) or (BY_ID[category].polarity == "positive" and _WISH.search(clause)):
        return True
    negatives = list(_NEGATIVE.finditer(window))
    if not negatives:
        return False
    if category in ("tout", "bribe") and _WARNING.search(clause):
        return False
    sentence_start, sentence_end = _sentence(text, start, end)
    if _TURNS_INTO_CLAIM.search(text[end:sentence_end]):
        return False
    if negatives[-1].group(0).lower() == "without":
        # "no work is done without bribe": "without" after an earlier negative is a claim. An earlier
        # "without" doesn't count: "without paying any bribe and without using an agent" is two denials.
        without_at = start - len(clause) + clause.rfind(negatives[-1].group(0))
        before = text[sentence_start:max(sentence_start, without_at)]
        if any(n.group(0).lower() != "without" for n in _NEGATIVE.finditer(before)):
            return False
    return True


def _excepted(category: str, text: str, start: int, end: int) -> bool:
    if not _EXCEPTIONS[category]:
        return False
    left, right = _sentence(text, start, end)
    return any(e.search(text[left:right]) for e in _EXCEPTIONS[category])


def find(text: str, source: Source = "text") -> list[Hit]:
    """Every category reported in a text, earliest first, at most one hit per category."""
    hits: dict[str, Hit] = {}
    plain = text.replace("\u2019", "'")  # curly apostrophes ("didn’t"), same length so offsets hold
    for category, language, pattern in _COMPILED:
        for m in pattern.finditer(plain):
            if _negated(plain, m.start(), m.end(), language, category) or _excepted(category, plain, m.start(), m.end()):
                continue
            hit = Hit(category, language, m.start(), m.end(), text[m.start():m.end()], source)
            if category not in hits or hit.start < hits[category].start:
                hits[category] = hit
            break
    return sorted(hits.values(), key=lambda h: h.start)


def classify(text: str, original: str = "", rating: float | None = None) -> dict[str, Hit]:
    """Categories a review reports, from the reviewer's own words first, then Google's translation.

    Praise words in a one-star review are almost always sarcasm ("how efficient this office
    is"), so positive hits are dropped when the review's rating is 1.
    """
    hits = {h.category: h for h in find(original, "original")} if original else {}
    for h in find(text, "text"):
        hits.setdefault(h.category, h)
    if rating is not None and rating <= 1:
        hits = {c: h for c, h in hits.items() if BY_ID[c].polarity != "positive"}
    return hits
