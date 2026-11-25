"""Check the language of Python examples without evaluating code or its literals."""

import keyword
import re
from io import StringIO
from tokenize import COMMENT, NAME, TokenError, generate_tokens
from unicodedata import normalize

_IDENTIFIERS = frozenset(
    [
        "afficher",
        "ajouter",
        "boite",
        "chaine",
        "choisir",
        "cle",
        "cles",
        "compter",
        "donnees",
        "entree",
        "erreur",
        "etat",
        "exemple",
        "fichier",
        "fichiers",
        "initialiser",
        "lecteur",
        "longueur",
        "mettre",
        "mot",
        "mots",
        "nettoyer",
        "normaliser",
        "nombre",
        "noms",
        "obtenir",
        "ouvrir",
        "parametres",
        "poids",
        "rechercher",
        "reponse",
        "requete",
        "resultat",
        "resultats",
        "sauvegarder",
        "sortie",
        "taille",
        "utilisateurs",
        "valeur",
        "valeurs",
        "verifier",
    ]
)
_COMMENT_WORDS = frozenset(
    [
        "au",
        "aux",
        "avec",
        "ce",
        "cet",
        "cette",
        "chaque",
        "dans",
        "de",
        "des",
        "du",
        "en",
        "est",
        "et",
        "fait",
        "il",
        "la",
        "le",
        "les",
        "nous",
        "on",
        "ou",
        "par",
        "pas",
        "pour",
        "qui",
        "si",
        "son",
        "sur",
        "un",
        "une",
        "vos",
        "vous",
    ]
)
_CAMEL_CASE = re.compile(r"(?<=[a-z])(?=[A-Z])")
_WORDS = re.compile(r"[^\W\d_]+")


def _words(text: str) -> set[str]:
    folded = normalize("NFKD", _CAMEL_CASE.sub(" ", text).casefold())
    letters = "".join(char for char in folded if char.isascii())
    return set(_WORDS.findall(letters))


def python_language_problems(code: str, first_line: int, *, show_input: bool = True) -> list[str]:
    """Report recognizable French identifiers and comments with their chapter line numbers."""
    problems: list[str] = []
    seen: set[str] = set()
    try:
        for token in generate_tokens(StringIO(code).readline):
            value = token.string
            row = first_line + token.start[0] - 1
            if token.type == NAME and value not in seen and not keyword.iskeyword(value):
                seen.add(value)
                if _words(value) & _IDENTIFIERS:
                    identifier = f'identifier "{value}"' if show_input else "identifier"
                    problems.append(f"Write the {identifier} in English (line {row}).")
            if token.type == COMMENT and len(_words(value) & _COMMENT_WORDS) >= 2:
                problems.append(f"Write the Python comment in English (line {row}).")
    except (TokenError, IndentationError):
        # A snippet can omit parts of the code to illustrate one step.
        pass
    return problems
