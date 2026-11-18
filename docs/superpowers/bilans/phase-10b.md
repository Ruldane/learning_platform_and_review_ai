# Phase 10b · Parcours joués via MCP

- Branche `phase-10b`. Le prompt de reprise se trouve dans `.superpowers/prompt-codex-10b.md`.
- Le catalogue `agents_play_list` expose une entrée pour chacun des 23 graphes, selon la portée
  du jeton. `agents_play_start`, `agents_play_brief` et `agents_play_submit` pilotent la
  session. Le guide des appels se trouve dans [docs/mcp/AGENTS.md](../../mcp/AGENTS.md).
- Chaque session jouée conserve son client et le runner enregistre les rendus à 0 $ dans
  `llm_calls`. Les validations personnelles se font dans Tremplin.

## Fonctionnalités vérifiées par les tests ciblés

| Fonctionnalité | Vérification |
| --- | --- |
| Conseil et Constructeur | Cadrage et choix humains, prise de parole en cours conservée, brouillon corrigé, validation |
| Leçons et quiz | Leçon publiée après vérification, questions et fiches enregistrées, tentative existante corrigée |
| Mémoire et compétences | Document appris et acquis déclaré, ajout de compétence isolé par compte et annulable |
| Recherche | Requête et lecture jouées, rejet d'une URL invalide, notation et enregistrement des sources |
| Étude et replanification | Questions du Tuteur et réponses humaines, aperçu de replanification |
| Projets | Énoncé, évaluation et brouillons |
| Candidatures | Création après confirmation, kit de sept pièces, entretien, comité de quatre personas et synthèse |
| Offres | Analyse d'écart, capture et lots du radar |
| CV | Brouillon de profil d'après un PDF existant, images MCP, deux passes du Maquettiste et validation, revue avec plusieurs rôles |
| IDE | Indice du professeur et exercice vérifié dans le faux bac à sable |
| Brief et démo | Conseil enregistré à la demande, orateurs de la démo et décision humaine |

Les tests utilisent des réponses scriptées, des fichiers et des comptes de test. Ils n'appellent
ni fournisseur LLM réel, ni réseau de recherche. La création du profil maître, les réponses au
quiz et le dépôt du travail d'un projet restent des gestes personnels.

## Niveaux ajoutés

| Outil | Niveau |
| --- | --- |
| `agents_play_list`, `agents_play_brief` | 1 |
| `agents_play_start`, `agents_play_submit`, `skills_write_skill` | 2 |

`python -m scripts.mcp_levels` depuis `backend` imprime la table complète. Les alias IDE,
CV, brief du jour et démo se découvrent avec `agents_play_list` et se lancent sous
`agents_play_start`. Pour le CV, utiliser les identifiants des PDF déposés dans Tremplin.

## Contrôles de régression

- Front. La suite complète est passée avec 2 866 tests. Les 21 tests ciblés des libellés et
  coûts sont passés après l'ajout des derniers cas.
- Backend. Sur la campagne élargie initiale, 1 677 tests sont passés et cinq ont signalé des
  écarts. Les contrôles ciblés ont validé les corrections du nom de l'outil IDE, du garde
  multipart, de la migration, du contrat CV et du rejeu de recherche.
- Le contrat OpenAPI et les types TypeScript ont été régénérés. Les neuf contrats d'imports
  et le contrôle mypy passent.
- Backend, suite complète (6 463 tests collectés, 38 exclus `live`/`sandbox_live`) : trois
  échecs, tous corrigés le 18 novembre.
  - Deux gardes d'isolation. `play_router` était inclus en tête du routeur des sessions, si
    bien que le garde nommait ce routeur d'après lui. Il devient une entrée de
    `FEATURE_ROUTERS`, placée avant `sessions_router` pour que `/sessions/play` passe avant
    `/{session_id}`, avec son cas d'isolation (`test_played_sessions.py`).
  - `test_openapi_exposes_session_types` ignorait le statut `expired`, voulu par la phase.
  - Après correction : 358 tests passent (isolation, sessions, MCP), ainsi que les 1 477 de la
    fin de la suite (fournisseurs, scripts, contrats, démarrage) et les 247 encore marqués en
    échec dans le cache pytest. Le contrat OpenAPI perd seulement le tag `sessions` en double.

## Recette MCP sur la pile de test (check11, sans clé)

- Conseil joué entièrement par Claude Code : 46 appels `provider=mcp`, coût 0 $. Le passage de
  rôle en rôle, les réponses du cadrage, les recherches et lectures du client, le refus motivé d'une
  sortie invalide puis la reprise, la règle « Objection : », l'arrêt anticipé quand l'avis est
  stable : tout est vérifié. Le Constructeur hérite de `played_by` après le choix fait dans l'interface.
- Trouvé : un brouillon de programme dont les tâches dépassent la plus longue journée fait échouer
  `program_builder` sur `planning_impossible`. Le message parle du budget hebdomadaire, et la
  session n'est pas renvoyée au Stratège. Le même défaut existe sans MCP : il est reporté en phase 11.
- Trouvé : la limite de 10 écritures par minute (`writes_per_minute`) répond 429 pendant la
  notation par source. Le client doit attendre le délai, ce que le relais et sa consigne font.
- Corrigé : refaire le programme depuis « Choisir », relancer les brouillons, les leçons, le quiz
  et le rendu de projet reprennent la source de la session d'origine.

## Lancement depuis Tremplin (D218)

- Menu « Qui fait tourner les agents » dans le panneau et dans Réglages > Modèles. L'en-tête
  `X-Tremplin-Run` est gardé sur la session (`played_by` ou `model_provider`, migration 0018).
- Relais `relay/` : il lance Claude Code ou Codex pour les sessions jouées en attente. Il démarre
  avec Windows et respecte les 429.
- Version courte, à la demande de January (quota) : un menu global au lieu d'un menu par bouton,
  et aucun test ajouté pour l'en-tête, le menu ni le relais. Les tests de bout en bout reprennent
  en phase 11.
- Profil LinkedIn lu jusqu'à 40 pages, et le CV toujours limité à 4 pages (D219).

## À terminer ou à vérifier

- Essai final de bout en bout sur check11 : menu sur « Claude Code (MCP) », validation du
  programme, leçons jouées par le relais, coût 0.
- Phase 11 : recette d'un programme complet, menu par bouton de lancement, appairage du relais
  en un clic, tests de l'en-tête, du menu et du relais, renvoi de `planning_impossible` au
  Stratège. Pour le Maquettiste, vérifier que le client interprète les images MCP.
