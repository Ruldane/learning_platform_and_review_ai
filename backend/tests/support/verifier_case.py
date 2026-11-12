"""Cas réel anonymisé du contrôle de fin de phase 4 (GLM 5.3 flash, module « Environnement et
outils ») : des passages de la leçon et les affirmations que le Vérificateur a relevées au fil de
ses trois contrôles, telles qu'il les a écrites (citation entre « », coupes par « ... »). Le
prénom de l'apprenante est remplacé, les numéros de source ramenés à `[1]` et `[2]`."""

from tests.support.lessons import lesson_markdown

OBJECTIVE = (
    "- Comprendre pourquoi Python et Git basique sont les fondations du métier d'AI engineer."
)
PREREQUISITE = (
    "Aucun prérequis technique : ce module est le point de départ du programme [2]. Une "
    "familiarité élémentaire avec le Web et un terminal est un plus [1]."
)
ESSENTIAL = (
    "- Un problème d'installation de package avec pip se règle le plus souvent en créant un "
    "environnement virtuel [1]."
)
PYTHON = (
    "Python est un langage polyvalent qui sert aussi bien à automatiser des tâches répétitives "
    "(envoyer des e-mails, écrire dans des fichiers) qu'à construire des applications [1]. Pour "
    "le métier visé par Alice — AI product engineer — c'est la langue maternelle de "
    "l'écosystème : les frameworks spécialisés s'utilisent en Python [2]."
)
EDITOR = (
    "### Choisir son éditeur Python\n\n"
    "VS Code est aujourd'hui l'outil le plus complet pour Python [2]. Pour ce module, restons\n"
    "sur **VS Code** : c'est aussi là que Git s'intègre le plus naturellement [2]."
)
STEP = (
    "**Étape 4 — Exécuter.** Dans le terminal intégré de VS Code, lancez `python decoupage.py` "
    "[1]. Vous devez voir deux passages s'afficher."
)
CODE = "```powershell\n# Dans le terminal intégré de VS Code, lancez python decoupage.py\n```"
MISTAKES = (
    "- **Confondre `python` et `python3`** : sous Linux ou macOS, utilisez `python3` [1].\n"
    "- **Ignorer le versionnage** : sans commits, impossible de revenir en arrière [2]."
)

C_APPS = (
    "« Python ... sert aussi bien à automatiser des tâches répétitives ... qu'à construire des "
    "applications [1] » : la source [1] mentionne l'automatisation et l'extraction de données, "
    "mais pas la construction d'applications."
)
C_OBJECTIVE = (
    "Objectif « comprendre pourquoi Python et Git basique sont les fondations du métier d'AI "
    "engineer » : aucune source ne présente Git comme une fondation du métier ; les sources "
    "citent Git comme outil de versionnement [2] sans lui donner ce rôle fondateur."
)
C_NAME = (
    "« Pour le métier visé par Alice — AI product engineer » : le nom « Alice » et l'existence "
    "de ce programme ne figurent dans aucune source numérotée."
)
C_TERMINAL = (
    "« Dans le terminal intégré de VS Code, lancez python decoupage.py » : l'existence d'un "
    "terminal intégré dans VS Code n'est mentionnée dans aucune source [1][2]."
)
C_PIP = (
    "« Un problème d'installation de package avec pip se règle le plus souvent en créant un "
    "environnement virtuel » : la source [1] dit que dans de nombreux cas la bonne solution est "
    "de contacter le développeur du package."
)
C_PREREQUISITE = (
    "« ce module est le point de départ du programme [2] » : la source [2] est une fiche métier, "
    "elle ne dit rien d'un programme de formation ni de son premier module."
)
C_GIT = (
    "« c'est aussi là que Git s'intègre le plus naturellement [2] » : [2] ne hiérarchise pas les "
    "éditeurs sur Git ; il attribue à PyCharm une « excellente gestion de Git »."
)
C_ABSENT = "« Python a été créé en 1989 aux Pays-Bas » : aucune source ne donne cette date."


def real_case_lesson(words: int = 1400) -> str:
    """Leçon valide (contrôles déterministes satisfaits) portant les passages du cas réel."""
    markdown = lesson_markdown(words)
    for anchor, extra in [
        ("- Savoir lire un masque causal [2].\n", OBJECTIVE + "\n"),
        ("Les produits matriciels et la fonction softmax.\n", "\n" + PREREQUISITE + "\n"),
        ("## Explication\n\n", PYTHON + "\n\n" + EDITOR + "\n\n"),
        ("étape par étape.\n", "\n" + STEP + "\n\n" + CODE + "\n"),
        ("Oublier la normalisation par la racine de la dimension.\n", "\n" + MISTAKES + "\n"),
    ]:
        assert anchor in markdown, anchor
        markdown = markdown.replace(anchor, anchor + extra, 1)
    return markdown.replace("- L'attention pondère les positions [1].\n", ESSENTIAL + "\n", 1)
