"""Les noms propres d'un texte écrit au nom de January (contrôle `text_claims`) : une entreprise ou
un outil que le profil ne nomme pas. Une lettre est de la prose : contrairement à une ligne de CV,
un nom y ouvre aussi une phrase (« Capgemini m'a confié… ») ou s'écrit en capitales (« chez IBM »).

Sont vérifiés : les mots en capitales de 2 lettres ou plus (sauf `ACRONYMS`), les mots capitalisés
hors début de phrase, ceux qui suivent « chez », « at », « pour »… même en début de phrase, et
ceux qui ouvrent une phrase suivis d'un verbe (« X m'a », « X a été »). Ne sont jamais des noms :
les formules d'adresse et destinataires génériques (`GREETINGS`), les mois et jours, les noms qui
suivent une salutation (« Bonjour Julie »). Un saut de ligne ouvre une phrase."""

import re

from app.agents.tools.posting_schema import normalize_term

_WORD = re.compile(r"\w[\w+#]*")
_SENTENCE_END = re.compile(r"[.!?\n]")
_MIN_NAME = 3

# Sigles courants d'une lettre, jamais un employeur (liste courte à dessein : tout autre sigle est
# rendu, un humain le lève).
ACRONYMS = frozenset("CV IA AI RH HR IT PDF CDI CDD PME ESN OK FR EN UE EU PS".split())  # noqa: SIM905
# Salutations : le nom qui les suit est celui du destinataire.
SALUTATIONS = frozenset(
    """bonjour bonsoir hello hi dear cher chere madame monsieur mademoiselle messieurs mesdames
    sir madam mr mrs ms mme mlle""".split()  # noqa: SIM905
)
# Formules d'adresse, destinataires génériques, mois et jours anglais.
GREETINGS = frozenset(
    SALUTATIONS
    | set(
        """hiring recruiter recruteur recruteuse equipe team cordialement regards sincerely merci
        thanks january february march april june july august september october november december
        monday tuesday wednesday thursday friday saturday sunday""".split()  # noqa: SIM905
    )
)
_EMPLOYER_CUES = frozenset("chez at pour for avec with rejoint joined".split())  # noqa: SIM905
_FOLLOWERS = frozenset("m me nous a ont est était etait has had was gave taught hired".split())  # noqa: SIM905
# Mots de phrase qui ressemblent à un sujet nommé sans en être un.
_SUBJECT_WORDS = frozenset(
    """cela ceci tout elle elles ils nous vous cette ces ceux celle celui chacun personne rien
    this that everything she they""".split()  # noqa: SIM905
)


def _is_caps(word: str) -> bool:
    return len(word) >= 2 and word.isalpha() and word.isupper()


def _starts_sentence(text: str, before: int, start: int) -> bool:
    return before < 0 or bool(_SENTENCE_END.search(text[before:start]))


def name_claims(text: str, known: str) -> list[tuple[int, str]]:
    """Les noms propres de `text` absents de `known` (un texte normalisé entre espaces) :
    `(position, mot tel qu'écrit)`, un par forme comparée, dans l'ordre du texte."""
    matches = list(_WORD.finditer(text))
    forms = [normalize_term(m.group(), plural=True) for m in matches]
    found: dict[str, tuple[int, str]] = {}
    greeting = 0  # noms à passer après une salutation
    for rank, match in enumerate(matches):
        word, form = match.group(), forms[rank]
        if form in SALUTATIONS:
            greeting = 2
            continue
        if greeting and word[0].isupper():
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
