"""Règles du contrôle de la phase 7 (`check_phase7`), en fonctions pures : chacune lit une réponse
de l'API déjà reçue (pièces du kit, archive) ou les journaux du back, et lève `CheckFailed` quand
une règle n'est pas tenue. Les messages ne portent que des étapes, des nombres, des rangs et des
noms de pièces : jamais le texte d'une pièce, un terme signalé, une entreprise ou un contact."""

import io
import re
import zipfile
from typing import Any

from scripts.phase4_rules import CheckFailed
from scripts.phase6_rules import LOG_FORBIDDEN as PHASE6_FORBIDDEN
from scripts.phase6_rules import plain

KIT_ORDER = ("cv", "letter", "linkedin", "followups", "form_answers", "company_brief", "pitch")
SALARY_BLANK = "À remplir par toi"
TO_COMPLETE = "À compléter"
LETTER_WORDS = (250, 350)
PITCH_WORDS = (130, 170)
MESSAGE_MAX_WORDS, FOLLOWUP_MAX_WORDS, INVITATION_MAX_CHARS = 150, 120, 300
WRITTEN = ("letter", "linkedin", "followups", "form_answers", "pitch")
_SALARY_TERMS = frozenset((
    "salaire", "salariale", "salarial", "remuneration", "pretention", "salary", "compensation",
    "package", "tjm", "brut",
))  # fmt: skip
_FRENCH = frozenset((
    "le", "la", "les", "de", "des", "du", "et", "un", "une", "pour", "je", "vous", "votre",
    "dans", "avec", "que", "est", "au", "aux", "sur", "en", "ce", "qui", "mon", "ma", "mes",
    "nos", "notre", "ai", "suis", "sont", "cette", "ces", "par", "plus", "ou", "mais",
    "vos", "j", "m", "l", "d",
))  # fmt: skip
_ENGLISH = frozenset((
    "the", "and", "to", "of", "in", "for", "with", "my", "your", "is", "are", "on", "that",
    "this", "as", "at", "it", "be", "have", "an", "a", "from", "by", "or", "but", "our",
    "their", "i", "you", "we",
))  # fmt: skip
_SKIPPED_KEYS = frozenset({"id", "sources", "email", "phone", "links", "url"})
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

# Ce que les journaux ne contiennent jamais (17.2) : tout ce que le contrôle de la phase 6
# écarte, plus ce que la phase 7 écrit : entreprises et intitulés des fiches de contrôle,
# contact, lien, phrase, brouillons de relance (gabarits), pièces du kit et archive.
PHASE7_FORBIDDEN = (
    "Développeuse IA",
    "Atelier Relance",
    "Maison Contrôle",
    "Alex Contrôle",
    "alex-controle-fictif",
    "controle-phase-7",
    "offres.example.org",
    "j'ai postulé hier",
    "Je me permets de revenir vers vous pour savoir si ma candidature",
    "Ce poste m'intéresse toujours et je reste disponible",
    "Aucune question éliminatoire repérée",
    "Non trouvé dans les sources lues",
    "Rien n'est envoyé par l'application",
    SALARY_BLANK,
)
LOG_FORBIDDEN = (*PHASE6_FORBIDDEN, *PHASE7_FORBIDDEN)


def check_logs(step: str, logs: str, extra: tuple[str, ...] = ()) -> int:
    """Aucune donnée personnelle dans les journaux ; rend le nombre de lignes lues. `extra` : des
    textes de ce passage (entreprise de la phrase)."""
    found = [rank for rank, needle in enumerate((*LOG_FORBIDDEN, *extra)) if needle in logs]
    if found:
        ranks = ", ".join(str(rank) for rank in found)
        raise CheckFailed(step, f"Donnée personnelle dans les journaux (motifs n° {ranks}).")
    return len(logs.splitlines())


def profile_text(data: Any) -> str:
    """Les textes des faits d'un profil (sans identifiants, origines, contact ni liens)."""
    parts: list[str] = []
    if isinstance(data, str):
        parts.append(data)
    elif isinstance(data, dict):
        parts += [profile_text(v) for k, v in data.items() if k not in _SKIPPED_KEYS]
    elif isinstance(data, list):
        parts += [profile_text(item) for item in data]
    return " ".join(parts)


def _tokens(text: str) -> list[str]:
    return [word.rstrip("s") or word for word in plain(text).split()]


def term_in_profile(term: str, profile: str) -> bool:
    """Le terme figure dans le profil (mots entiers, sans accents ni casse ni pluriel)."""
    wanted = _tokens(term)
    if not wanted:
        return False
    return f" {' '.join(wanted)} " in f" {' '.join(_tokens(profile))} "


def words_of(text: str) -> int:
    return len(text.split())


def speaks(text: str, language: str) -> bool:
    """Le texte est écrit dans la langue (`fr` ou `en`) : plus de mots courants de cette langue
    que de l'autre, et au moins 8 % du texte."""
    tokens = plain(text).split()
    french = sum(1 for token in tokens if token in _FRENCH)
    english = sum(1 for token in tokens if token in _ENGLISH)
    own, other = (english, french) if language.startswith("en") else (french, english)
    return bool(tokens) and own > other and own >= 0.08 * len(tokens)


def split_parts(content: str) -> list[str]:
    """Les textes séparés par une ligne `---`."""
    parts: list[list[str]] = [[]]
    for line in content.splitlines():
        if line.strip() == "---":
            parts.append([])
        else:
            parts[-1].append(line)
    return ["\n".join(lines).strip() for lines in parts]


def _between(step: str, kind: str, count: int, low: int, high: int) -> None:
    if not low <= count <= high:
        raise CheckFailed(step, f"Pièce {kind} : {count} mot(s), de {low} à {high} attendus.")


def check_letter(step: str, item: dict[str, Any], language: str) -> int:
    """Lettre de 250 à 350 mots, dans la langue de l'offre ; rend le compte de mots."""
    count = words_of(item["content"])
    _between(step, "letter", count, *LETTER_WORDS)
    if not speaks(item["content"], language):
        raise CheckFailed(
            step, f"Pièce letter : pas écrite dans la langue de l'offre ({language})."
        )
    return count


def check_lengths(step: str, item: dict[str, Any]) -> None:
    """Les bornes de mots des autres pièces écrites ; seules les pièces prêtes y sont tenues (une
    pièce « à vérifier » peut les avoir ratées au nouvel essai)."""
    if item["status"] != "ready":
        return
    kind, parts = item["kind"], split_parts(item["content"])
    if kind == "pitch":
        _between(step, kind, words_of(item["content"]), *PITCH_WORDS)
    elif kind == "linkedin":
        if len(parts) != 2 or len(parts[0]) > INVITATION_MAX_CHARS:
            raise CheckFailed(step, "Pièce linkedin : invitation et message attendus, 300 signes.")
        _between(step, kind, words_of(parts[1]), 1, MESSAGE_MAX_WORDS)
    elif kind == "followups":
        if len(parts) != 2:
            raise CheckFailed(step, "Pièce followups : deux relances attendues.")
        for part in parts:
            _between(step, kind, words_of(part), 1, FOLLOWUP_MAX_WORDS)


def _is_salary(question: str) -> bool:
    return any(token in _SALARY_TERMS for token in _tokens(question))


def check_form(step: str, item: dict[str, Any]) -> int:
    """Aucune réponse salariale remplie : chaque question salariale du formulaire est laissée à
    January. Rend le nombre de questions salariales trouvées."""
    asked = 0
    question = ""
    for line in item["content"].splitlines():
        if line.startswith("### "):
            question = line[4:]
            asked += _is_salary(question)
    answers = _form_answers(item["content"])
    for text, answer in answers:
        if _is_salary(text) and answer != SALARY_BLANK:
            raise CheckFailed(step, "Pièce form_answers : une réponse salariale est remplie.")
    if item["salary_fields"] != sum(1 for _, a in answers if a == SALARY_BLANK):
        raise CheckFailed(step, "Pièce form_answers : `salary_fields` différent du contenu.")
    return asked


def _form_answers(content: str) -> list[tuple[str, str]]:
    items: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        if line.startswith("### "):
            items.append((line[4:].strip(), []))
        elif items:
            items[-1][1].append(line)
    return [(question, "\n".join(lines).strip()) for question, lines in items]


def _bounds_broken(item: dict[str, Any]) -> bool:
    """Les mots de la pièce sont hors de leurs bornes (le nouvel essai ne les a pas tenues)."""
    try:
        if item["kind"] == "letter":
            _between("", "letter", words_of(item["content"]), *LETTER_WORDS)
        check_lengths("", {**item, "status": "ready"})
    except CheckFailed:
        return True
    return False


def check_to_check(step: str, item: dict[str, Any], profile: str) -> int:
    """Une pièce « à vérifier » dit pourquoi : ses termes (absents du profil, tous), des mots hors
    bornes, ou une réponse laissée vide. Rend le nombre de termes."""
    kind = item["kind"]
    flags = [str(flag) for flag in item["flags"]]
    present = [str(rank) for rank, flag in enumerate(flags) if term_in_profile(flag, profile)]
    if present:
        raise CheckFailed(step, f"Pièce {kind} : terme(s) n° {', '.join(present)} au profil.")
    written = kind in ("letter", "linkedin", "followups", "pitch")
    if written and not flags and not _bounds_broken(item):
        raise CheckFailed(step, f"Pièce {kind} « à vérifier » sans terme nommé.")
    if kind == "form_answers" and not flags and not _has_blank(item):
        raise CheckFailed(step, "Pièce form_answers « à vérifier » sans terme ni réponse vide.")
    return len(flags)


def _has_blank(item: dict[str, Any]) -> bool:
    return any(a in (SALARY_BLANK, TO_COMPLETE) for _, a in _form_answers(item["content"]))


def check_dossier(step: str, item: dict[str, Any]) -> int:
    """Le dossier de l'entreprise : au moins une source, chaque citation `[n]` en désigne une.
    Rend le nombre de sources."""
    sources = item["sources"]
    if not sources:
        raise CheckFailed(step, "Dossier de l'entreprise sans aucune source.")
    ranks = [source["rank"] for source in sources]
    if ranks != list(range(1, len(ranks) + 1)):
        raise CheckFailed(step, "Sources du dossier : rangs non continus depuis 1.")
    if not all(str(s["url"]).startswith(("http://", "https://")) for s in sources):
        raise CheckFailed(step, "Source du dossier sans lien http(s).")
    cited = {
        int(n) for found in _CITATION.findall(item["content"]) for n in re.findall(r"\d+", found)
    }
    if not cited:
        raise CheckFailed(step, "Dossier de l'entreprise sans citation [n].")
    if max(cited) > len(sources):
        raise CheckFailed(step, f"Citation [{max(cited)}] sans source ({len(sources)} lue(s)).")
    return len(sources)


def check_items(step: str, items: list[dict[str, Any]]) -> None:
    """Sept pièces, dans l'ordre fixe, aucune en attente ni en échec."""
    kinds = tuple(item["kind"] for item in items)
    if kinds != KIT_ORDER:
        raise CheckFailed(step, f"{len(items)} pièce(s) rendue(s), l'ordre fixe de 7 est attendu.")
    bad = [f"{i['kind']} ({i['status']})" for i in items if i["status"] in ("pending", "failed")]
    if bad:
        raise CheckFailed(step, f"Pièce(s) non produite(s) : {', '.join(bad)}.")
    empty = [i["kind"] for i in items if not i["content"].strip()]
    if empty:
        raise CheckFailed(step, f"Pièce(s) vide(s) : {', '.join(empty)}.")


def check_zip(step: str, body: bytes, items: list[dict[str, Any]]) -> int:
    """L'archive est lisible, une pièce par fichier (même texte), le PDF du CV, le LISEZMOI qui
    nomme les pièces à vérifier. Rend le nombre de fichiers."""
    if not zipfile.is_zipfile(io.BytesIO(body)):
        raise CheckFailed(step, "kit.zip : ce n'est pas une archive ZIP.")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        if archive.testzip() is not None:
            raise CheckFailed(step, "kit.zip : un fichier de l'archive est corrompu.")
        names = archive.namelist()
        for rank, item in enumerate(items, 1):
            if item["status"] in ("ready", "to_check"):
                name = f"{rank:02d}_{item['kind']}.md"
                if name not in names:
                    raise CheckFailed(step, f"kit.zip : fichier {name} absent.")
                if archive.read(name).decode("utf-8").strip() != item["content"].strip():
                    raise CheckFailed(step, f"kit.zip : {name} différent de la pièce.")
        pdfs = [n for n in names if n.startswith("CV_") and n.endswith(".pdf")]
        if not pdfs or not archive.read(pdfs[0]).startswith(b"%PDF"):
            raise CheckFailed(step, "kit.zip : le PDF du CV manque ou n'est pas un PDF.")
        readme = archive.read("LISEZMOI.txt").decode("utf-8") if "LISEZMOI.txt" in names else ""
        if not readme:
            raise CheckFailed(step, "kit.zip : LISEZMOI.txt absent.")
        for rank, item in enumerate(items, 1):
            if item["status"] == "to_check" and f"{rank:02d}_{item['kind']}.md" not in readme:
                raise CheckFailed(step, f"LISEZMOI.txt : pièce {item['kind']} à vérifier non dite.")
        return len(names)
