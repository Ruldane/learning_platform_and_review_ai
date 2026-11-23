# Étape 3 : programmes de zéro à expert (plan directeur §8 et §8.1)

Branche `claude/programmes-zero-expert`, partie de `codex/reorganisation` (`8f04a17d`).
L'étape 2 (IDE dans la leçon) est reportée ; January l'a demandé le 2026-11-23.

## Constat de départ

- `PlanDraft` porte déjà un graphe des notions (`requires`, `introduces` par chapitre) et refuse
  un chapitre qui requiert une notion non introduite. Mais ces champs sont **facultatifs** : un
  sommaire sans graphe passe. Le message d'erreur ne nomme pas la notion, car `PlanDraft` sert
  aussi à l'écriture directe par l'API, et une 422 ne renvoie jamais l'entrée reçue (D303).
- Le Stratège n'a aucune notion d'étape (fondations, pratique courante, avancé), ne justifie
  pas la place d'une semaine et ne lit aucune documentation officielle.
- Pilote du 22/11 : les deux sources Aurelio datées de 2025 ont été écartées (note de 46), et
  aucune source officielle n'a été proposée à l'Éclaireur. Les révisions du Rédacteur ont fait
  baisser les notes et dépasser 2 500 mots. Il y a deux causes :
  - la consigne demande de « réécrire la leçon complète » sans donner la longueur de la
    version précédente ni les critères déjà réussis ;
  - la révision suivante repart toujours de la **dernière** version, même quand elle est moins
    bonne que la précédente.

## Tâche 1 : révisions du Rédacteur qui n'abîment plus le chapitre

- Le Vérificateur garde la **meilleure version** dans l'état (`best_draft`, `best_rank`). Le
  rang trie d'abord par le nombre de problèmes et d'affirmations non sourcées, puis par la plus
  basse des notes. Une révision part de la meilleure version, pas de la dernière.
- La consigne de révision devient **ciblée** :
  - la longueur de la version de départ et la borne de 2 500 mots ;
  - les critères déjà réussis, avec leur note, à ne pas toucher ;
  - « modifie seulement les passages visés ; recopie le reste tel quel » ;
  - au-dessus de la borne, raccourcir est la première correction.
- Tests : `tests/agents/` (rang, choix de la base de révision, rendu de la consigne).

## Tâche 2 : le programme garde l'étape, la justification et les sources officielles

- `WeekDraft` reçoit `stage` (`fondations` | `pratique` | `avance`, facultatif) et `rationale`
  (pourquoi cette semaine arrive à cette place, 300 caractères, facultatif).
- `ModuleDraft` reçoit `official_urls` (0 à 3 pages de la doc officielle) et `legacy`
  (0 à 5 API dépréciées ou devenues secondaires, à présenter en encadré « Lire du code
  ancien »).
- Ces champs restent facultatifs dans `PlanDraft`, pour ne pas casser l'écriture directe ni le
  MCP. Ils sont **obligatoires pour le Stratège** (tâche 3).
- Migration `0074` : `weeks.stage`, `weeks.rationale`, `modules.official_urls`,
  `modules.legacy`. Enregistrés par `drafting`, rendus par l'API du programme, puis contrat et
  `schema.d.ts` régénérés. La page du programme affiche l'étape et la justification de chaque
  semaine.
- `ModuleBrief.seed_urls` place les pages officielles **en tête**. Le Rédacteur reçoit `legacy`
  et le présente seulement dans un encadré « Lire du code ancien ».

## Tâche 3 : le Stratège écrit un livre, de zéro à expert, à jour de la doc officielle

- Nouveau nœud `docs` avant `draft` dans `program_builder` :
  - recherche « documentation officielle » du sujet par le port web ;
  - lecture de 3 pages au plus ;
  - le texte va au Stratège, encadré comme non fiable, avec la date de lecture.
  Sans réseau ou sans résultat, le programme s'écrit quand même, et la consigne le dit.
- Contrôles du livre (`agents/nodes/strategist/book_checks.py`). Leurs problèmes repartent au
  Stratège avec ceux de `check_draft`, et nomment la notion ou la semaine fautive :
  - chaque chapitre introduit au moins une notion ;
  - une notion requise doit avoir été introduite **avant**, et le message la nomme ;
  - chaque semaine a une `stage`, et les étapes ne reculent jamais. Un programme de 3 semaines
    ou plus passe par les trois étapes. La première semaine relève des fondations ;
  - chaque semaine a une `rationale` ;
  - si la doc officielle a été lue, chaque chapitre a au moins une `official_urls` prise parmi
    les pages lues ou sur le même domaine.
- La consigne `plan` du Stratège explique ces règles et donne l'exemple LangChain v1 : modèles
  et messages, puis prompts et sorties structurées, puis outils, puis `create_agent`, puis RAG,
  puis LangGraph, et LCEL en encadré.
- Tests : contrôles du livre (cas nommés), nœud `docs` avec un faux port web, rendu de la
  consigne, parcours `program_builder` avec un modèle scripté.

## Déroulé avec January (arrêts)

1. Code des tâches 1 à 3, contrôles verts et une relecture.
2. Essai réel sur une pile jetable `check2`, avec Claude :
   - nouveau sommaire LangChain **montré à January**, avec la justification de chaque semaine ;
   - **arrêt**.
3. Pilote de 2 à 3 chapitres relus par January. **Arrêt.**
4. Estimation du coût de reconstruction des quatre programmes. **Arrêt** jusqu'à son accord.
5. Reconstruction complète sur l'installation principale, avec vérification de chaque leçon.

## Décisions

D305 à D307 (fin de `DECISIONS.md`).
