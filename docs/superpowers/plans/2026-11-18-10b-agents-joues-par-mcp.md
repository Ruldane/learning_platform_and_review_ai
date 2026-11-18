# Phase 10b — Les agents de l'app joués par Claude ou Codex via MCP (cadrage)

> Cadrage validé par January le 18/11. Le code se fera **après le reset hebdo**. Le plan détaillé
> (tâches, tests) s'écrit au début de la phase, avec superpowers:writing-plans, à partir de ce
> cadrage.

## Principe (demande de January)

Le MCP doit pouvoir faire **tout ce que font les agents de l'app**, avec **le même comportement**.
Quand une fonctionnalité enchaîne plusieurs agents (par exemple un programme : Conseil →
Constructeur → Fabrique de leçons → Vérificateur), Claude Code ou Codex **joue chaque rôle à tour
de rôle** avec ses propres modèles. **Aucun appel à l'API de January** (0 $), mais le même chemin
de validation, de contrôle et d'enregistrement que l'agent interne.

## Mécanisme proposé : « rôle joué »

Pour chaque agent (nœud de graphe) qui appelle un LLM :

1. **`<parcours>_brief_<rôle>`** (niveau 1). Le MCP rend ce que le nœud recevrait :
   - consignes du rôle (le prompt système de l'agent, depuis la même source) ;
   - entrées (données lues par les ports, texte non fiable entouré comme donnée) ;
   - **schéma JSON de la sortie attendue** (le modèle Pydantic du nœud) ;
   - identifiant d'étape.
2. **`<parcours>_rendre_<rôle>`** (niveau 2, ou 3 si l'étape a un effet externe). La sortie de
   Claude passe par :
   - le **même** modèle Pydantic ;
   - les **mêmes** contrôles et vérificateurs (bornes, lexique du CV, chiffres, Mermaid, nombre
     de questions…) ;
   - les **mêmes** ports d'enregistrement.
   Un refus rend les raisons, comme l'agent interne ferait une nouvelle tentative.
3. **Séance d'agent jouée.** Une session de graphe est créée avec un mode « joué par MCP » :
   modèle `claude-code` ou `codex`, coût 0, journal des étapes. Le suivi de session existant
   (`graph_<nom>` en `follow_only`) la montre, et l'interface affiche « joué par Claude ».
4. **Enchaînement.** Le parcours garde son ordre : l'étape suivante n'ouvre son brief que lorsque
   la précédente est rendue. Les points de décision de January restent au niveau 3 :
   - choix d'une proposition du Conseil ;
   - validation du programme ;
   - entrée au profil maître…
5. **Moteur.** De préférence, réutiliser le graphe LangGraph tel quel, avec un **fournisseur LLM
   « MCP »**. Quand un nœud appelle le modèle, la session se met en pause (interruption LangGraph,
   déjà utilisée pour les questions à January) et publie le brief ; le rendu de Claude reprend la
   session comme réponse du modèle. Ainsi le comportement est **le même par construction** :
   mêmes nœuds, mêmes contrôles, mêmes tentatives.

## Portée

Les ~22 parcours, dont :

| Domaine | Parcours |
|---|---|
| Apprentissage | Conseil, `program_builder`, `lesson_factory`, `quiz`, `study_session`, `replan`, document appris |
| Recherche | `web_research` (Claude cherche avec ses propres outils, rend les sources) |
| Carrière | `capture`, `gap_analysis`, `market_radar`, `cv_capture`, `cv_review`, `application_kit`, comité d'embauche, `interview` |
| Quotidien et projets | `daily_brief`, `project_brief`, `project_review` |
| IDE | `ide_teacher`, `ide_exercise` |
| Démo | `demo_debate` |

L'écriture directe (10.W) et le programme direct (D213) restent : ils servent de rendu quand une
étape n'a pas besoin de contrôle d'agent.

## Questions à trancher au début de la phase

- Interruption LangGraph pour tous les nœuds, ou ports « rendus » par parcours. La première
  option donne le même comportement par construction ; elle est à vérifier sur 2 parcours avant
  de généraliser.
- Délai d'une étape en attente (brief non rendu), puis abandon propre.
- Les parcours planifiés (brief du jour, radar) : jouables à la demande seulement.
- Garde de couverture : tout nœud qui appelle un LLM a son brief et son rendu, ou une exclusion
  motivée.

## Estimation

Environ 6 à 10 % du quota hebdo. Ordre suggéré : la chaîne du programme d'abord (preuve du
mécanisme), puis carrière, puis le reste.
