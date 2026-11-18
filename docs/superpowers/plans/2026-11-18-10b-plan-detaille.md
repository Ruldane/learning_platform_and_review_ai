# Phase 10b · Plan d’implémentation

Le [cadrage validé](2026-11-18-10b-agents-joues-par-mcp.md) fixe la portée. Le premier lot
vérifie si un fournisseur peut interrompre puis reprendre **les graphes actuels** en conservant
l’association entre chaque demande et sa réponse. Les lots suivants dépendent de cette preuve.

**État au 18 novembre.** Les deux graphes passent la preuve locale. Le Conseil conserve le
verdict de chaque source après redémarrage et atteint le choix du parcours. Le Constructeur
enregistre le brouillon corrigé et attend la validation. Voir [D215](../../../DECISIONS.md#d215).

**Reprise de la phase.** Le catalogue de niveau 1 restitue les entrées des 23 graphes.
Les tests ciblés passent pour le Conseil, le Constructeur, les leçons, le quiz, le tutorat, la
replanification, le document appris, les projets, l'IDE, le brief du jour, les candidatures,
le radar, la revue de CV et la recherche jouée. La capture de CV reçoit les images en blocs
MCP et l'Archiviste écrit un brouillon sous validation humaine. Les vérifications intégrées
des reprises et la campagne de régression sont en cours. Voir
[le bilan de reprise](../bilans/phase-10b.md).

## 1. Conseil et Constructeur

- [x] Dans `backend/tests/agents/graphs/test_played_proof.py`, lancer les deux graphes avec
  `SessionRunner`, le checkpoint SQLite et les ports de test existants. Injecter le modèle par
  `GraphDeps.models`. Le faux client répond à chaque interruption avec une réponse propre au
  brief. Vérifier le cadrage humain, plusieurs sources avec des verdicts distincts dans le même
  nœud, le choix de la proposition, puis le brouillon du programme et sa validation humaine.
- [x] Vérifier la nouvelle tentative du Stratège après un JSON invalide. Comparer les messages
  reçus à ceux du fournisseur scripté. Vérifier le coût et l’absence de double écriture.
- [x] Exécuter `pytest tests/agents/graphs/test_played_proof.py -q`. Si le fournisseur seul
  associe une réponse à la mauvaise demande, consigner le contre-exemple en D214 et arrêter
  avant de brancher le MCP. Sinon consigner le mécanisme retenu et poursuivre.
- [x] Après preuve, enregistrer le client sur la session par migration Alembic. Sélectionner
  la source de modèles dans `runtime/execution.py` avant tout accès aux clés. Propager le client
  aux sessions filles, y compris après une confirmation dans l’interface ou un redémarrage.
- [x] Déclarer les outils génériques de lancement, lecture et rendu aux niveaux 2, 1 et 2.
  Réutiliser le lancement de la feature avec sa portée et ses préconditions. Réserver le rendu
  par compte, session et étape en base. Tester les soumissions concurrentes, le redémarrage
  après réservation, l’expiration à 24 h, l’annulation et la limite de lancements.
- [x] Dans les tests MCP et d’isolation, essayer une session étrangère (404), un jeton hors
  portée, un jeton en lecture seule et un rendu sur une décision humaine. Vérifier qu’une
  422, le journal et le brief respectent chacun leurs règles de confidentialité.
- [ ] Régénérer OpenAPI et les types TypeScript. Exécuter les tests ciblés et les hooks.
  Commit prévu après preuve verte : `feat(10b): jouer le Conseil et le Constructeur par MCP`.

## 2. Fabrique de leçons, Vérificateur et quiz

- [ ] Ajouter les cas de rendu valide, invalide puis corrigé aux tests des trois parcours,
  avec les mêmes ports et validateurs, y compris un refus du Vérificateur. Vérifier le résultat
  enregistré, le coût nul et l’absence de session payante parmi les enfants.
- [ ] Brancher les parcours après les échecs attendus. Tester le refus de répondre au quiz
  par MCP, rejouer les tests du premier lot, puis committer le groupe vert.

## 3. Autres parcours et garde de couverture

- [ ] Paramétrer les tests depuis `agents/graphs/registry.py` et les déclarations de lancement
  des features. Pour chaque parcours comparer prompt, contrôle, résultat et coût à une exécution
  scriptée. Couvrir aussi les branches de reprise, les appels parallèles et les réponses libres.
- [ ] Tester la recherche avec sources rendues par le client et les balises de texte non fiable.
  Tester le brief et le radar à la demande puis par le planificateur. Seul le déclenchement à
  la demande doit utiliser le modèle MCP.
- [ ] Couvrir les gestes réservés à l’utilisatrice, les écritures au profil maître et les
  jetons limités à une feature. Ajouter un garde qui échoue dès l’ajout d’un nœud LLM sans
  parcours testé ou exclusion motivée. Committer chaque groupe vérifié.

## 4. Interface et livraison

- [ ] Tester les anciens enregistrements et les deux libellés en français dans le suivi et
  le rapport des coûts. Ajouter les textes i18n et vérifier le rendu à zéro.
- [x] Documenter la chaîne du programme dans `docs/mcp/AGENTS.md`, mettre à jour la règle
  recopiée depuis `backend/app/mcp/instructions.py` et vérifier le test de recopie.
- [ ] Vérifier contrats générés, types, lint, longueurs et table `scripts.mcp_levels`.
  Exécuter une fois la suite back complète, les tests front et consigner résultats et
  exclusions dans `docs/superpowers/bilans/phase-10b.md`. Commits par chemins explicites.

## 5. Lancement des parcours depuis Tremplin

Ce chantier suit la validation du MCP. Il relie les boutons de lancement de Tremplin aux
clients locaux et aux fournisseurs de l'application.

- [ ] Proposer un seul menu sur les fonctionnalités qui lancent des agents. Les choix sont
  Claude Code, Codex, API Claude, API GLM et API OpenAI, selon les clients disponibles et
  les fournisseurs configurés.
- [ ] Brancher l'interface aux clients locaux pour qu'un lancement depuis Tremplin puisse
  utiliser la connexion du client choisi. Afficher sa disponibilité et conserver le choix
  pendant les attentes, reprises et sessions filles du parcours.
- [ ] Vérifier la chaîne complète depuis le bouton de la fonctionnalité jusqu'aux résultats
  dans Tremplin. Garder le suivi de chaque rôle et les décisions de January dans l'interface.
