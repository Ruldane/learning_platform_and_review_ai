"""The proper nouns of a text written in January's name (`text_claims` check): a company or
a tool that the profile does not name. A letter is prose: unlike a CV line,
a name there also opens a sentence ("Capgemini m'a confié...") or is written in capitals
("chez IBM").

Checked: words in capitals of 2 letters or more (except `ACRONYMS`), capitalised words
outside the start of a sentence, those that follow "chez", "at", "pour"... even at the start of a
sentence, and those that open a sentence followed by a verb ("X m'a", "X a été"). Never names:
the forms of address and generic recipients (`GREETINGS`), months and days, the names that
follow a greeting ("Bonjour Julie"). A line break opens a sentence. The French and English
word lists both stay: letters and CVs stored before the switch are French."""

import re

from app.agents.tools.posting_schema import normalize_term

_WORD = re.compile(r"\w[\w+#]*")
_SENTENCE_END = re.compile(r"[.!?\n]")
_CLAUSE_END = re.compile(r"[,.;:!?\n]")
_MIN_NAME = 3

# Common acronyms of a letter, never an employer (short list on purpose: any other acronym is
# flagged, a human lifts it).
ACRONYMS = frozenset("CV IA AI RH HR IT PDF CDI CDD PME ESN OK FR EN UE EU PS".split())  # noqa: SIM905
# Greetings: the name that follows is the recipient's.
SALUTATIONS = frozenset(
    """bonjour bonsoir hello hi dear cher chere madame monsieur mademoiselle messieurs mesdames
    sir madam mr mrs ms mme mlle""".split()  # noqa: SIM905
)
# Forms of address, generic recipients, English months and days.
GREETINGS = frozenset(
    SALUTATIONS
    | set(
        """hiring recruiter recruteur recruteuse equipe team cordialement regards sincerely merci
        thanks january february march april may june july august september october november december
        monday tuesday wednesday thursday friday saturday sunday""".split()  # noqa: SIM905
    )
)
_EMPLOYER_CUES = frozenset("chez at pour for avec with rejoint joined".split())  # noqa: SIM905
_FOLLOWERS = frozenset("m me nous a ont est était etait has had was gave taught hired".split())  # noqa: SIM905
# Sentence words that look like a named subject without being one.
_SUBJECT_WORDS = frozenset(
    """cela ceci tout elle elles ils nous vous cette ces ceux celle celui chacun personne rien
    this that everything she they""".split()  # noqa: SIM905
)


def _is_caps(word: str) -> bool:
    return len(word) >= 2 and word.isalpha() and word.isupper()


def _starts_sentence(text: str, before: int, start: int) -> bool:
    return before < 0 or bool(_SENTENCE_END.search(text[before:start]))


def name_claims(text: str, known: str) -> list[tuple[int, str]]:
    """The proper nouns of `text` absent from `known` (a normalised text between spaces):
    `(position, word as written)`, one per compared form, in text order."""
    matches = list(_WORD.finditer(text))
    forms = [normalize_term(m.group(), plural=True) for m in matches]
    found: dict[str, tuple[int, str]] = {}
    greeting = 0  # names to skip after a greeting
    for rank, match in enumerate(matches):
        word, form = match.group(), forms[rank]
        gap = text[matches[rank - 1].end() : match.start()] if rank else ""
        if _CLAUSE_END.search(gap):
            greeting = 0  # the greeting stops at its comma or its line break
        if form in SALUTATIONS:
            greeting = 2
            continue
        if greeting and word[0].isupper() and not word.isupper():
            greeting -= 1
            continue
        greeting = 0
        if form in GREETINGS or f" {form} " in known or form.isdigit():
            continue
        before = matches[rank - 1].end() if rank else -1
        after = matches[rank + 1].group().casefold() if rank + 1 < len(matches) else ""
        cued = rank > 0 and forms[rank - 1] in _EMPLOYER_CUES
        opens = _starts_sentence(text, before, match.start())
        if _is_caps(word):
            flagged = word not in ACRONYMS
        elif len(word) < _MIN_NAME or not word[0].isupper():
            flagged = False
        elif opens:
            flagged = cued or (after in _FOLLOWERS and form not in _SUBJECT_WORDS)
        else:
            flagged = True
        if flagged:
            found.setdefault(form, (match.start(), word))
    return list(found.values())
