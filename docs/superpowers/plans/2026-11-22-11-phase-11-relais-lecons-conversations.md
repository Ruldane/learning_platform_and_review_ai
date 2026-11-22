# Phase 11 — Relais, leçons et conversations

**Objectif.** Produire des chapitres vérifiés, ouvrir trois conversations ancrées dans les
sources, et terminer les corrections reportées de la phase 10b.

**Références.** Plan directeur, sections Phase 11, cadrage du 20 novembre et D218 à D221.
Conserver les tiers du registre de modèles. Les essais réels choisissent le fournisseur OpenAI.

## Contraintes

- Tests déterministes avec les fournisseurs factices, puis essai borné sur une pile jetable.
- Toute nouvelle entrée HTTP a un test d’isolation, une déclaration ou une exclusion MCP et un
  contrat régénéré. Les réglages et le canal de synchronisation restent hors MCP.
- Aucune publication de cours ni écriture sur le volume d’origine pendant les tests.
- Le pilote LangChain et le feu vert sur le coût précèdent la réécriture massive. La recette
  longue des clients MCP est également soumise à l’accord de coût du plan directeur.

## 1. Relais

- [x] Ajouter `relay/tremplin-relay.test.mjs`. Une interrogation vide par intervalle reste
  sous 1 000 appels par 24 h et en réserve au moins 250. Une 429 conserve son délai serveur.
  La liste d’arguments de Codex commence par `--search`, puis `exec`.
- [x] Dans `relay/tremplin-relay.mjs`, rendre testable le traitement d’un tour avec sa
  fonction d’appel injectée. Utiliser 120 s après un tour normal et comme délai minimum
  après une erreur de communication. Garder la pause par session et le parallélisme existants.
  Ne démarrer la boucle que quand Node exécute ce fichier comme point d’entrée.
- [x] Lancer `node --test relay/tremplin-relay.test.mjs` et documenter le délai et le budget.

## 2. Chapitres et table des matières

- [x] Rédiger la norme dans les consignes du Rédacteur. Conserver les tests de titre,
  de longueur et de structure. Couvrir le schéma placé hors de sa section ainsi que
  les identifiants et commentaires français courants dans les exemples Python.
- [ ] Tester l’application de la même validation au Rédacteur et aux écritures directes.
  Déclencher la Fabrique avec le brouillon fourni et garder la version publiée précédente
  jusqu’à publication de la nouvelle. Tester les refus avec raisons, la vérification qui
  redemande une révision et l’ajout de ressources seul sur un chapitre historique (D221).
- [x] Ajouter la grille structurée à `agents/nodes/verifier`. Tester qu’un vérificateur
  refuse un critère sous le seuil même si la moyenne passe. Conserver le contrôle des sources.
- [x] Tester qu’un prérequis non introduit dans un chapitre précédent est rendu au Stratège
  et que le glossaire et les chapitres voisins arrivent dans le brief. Préserver la lecture
  des anciens instantanés.
- [ ] Vérifier sur le pilote que le premier chapitre pose bien les fondations.
- [x] Orienter les nouvelles leçons vers la Fabrique dans le guide et les consignes MCP.
  Adapter les réponses scriptées à la nouvelle grille.
- [ ] Vérifier le brief et la norme pendant la recette réelle avec le client MCP.
- [ ] Générer deux ou trois chapitres LangChain en pilote sur la pile jetable. Contrôler la
  structure, les sources, les notes du Vérificateur et le coût avant de présenter le résultat.

## 3. Conversations partagées

- [ ] Tester dans une nouvelle feature `conversations` la persistance d’un fil et des sources,
  l’isolation entre comptes, une reprise sans doublon et un dépassement de budget. Réutiliser
  les sessions et fournisseurs existants pour lancer la réponse sans bloquer la requête.
- [ ] Partager les briques du chat IDE. Ajouter le panneau du professeur au lecteur, lié à la
  leçon et au passage courant. Tester au clavier le retour du focus et la réouverture du fil.
- [ ] Relier le training au suivi d’étude. Tester les trois modes, leur changement pendant le
  fil, l’exclusivité avec une séance guidée et l’enregistrement des fiches et preuves sans
  cocher de tâche planifiée.
- [ ] Relier Cerveau à la mémoire. Tester le remplacement et le retrait des extraits, la
  reprise après une coupure et l’ignorance des jonctions et dossiers techniques. Réutiliser
  les contrôles d’ingestion, lier chaque fichier à son dossier et réserver la gestion des
  chemins au compte connecté. Le relais envoie les fichiers autorisés sous un jeton distinct.
- [ ] Déclarer les entrées MCP et ajouter les tests Playwright du professeur, du training et
  d’une note retrouvée puis retirée. Vérifier que les liens de sources ouvrent le bon document.

## 4. Reports de la phase 10b

- [ ] Tester les choix fournisseur par lancement et l’héritage dans les reprises et sessions
  enfants. Conserver le réglage global pour les lancements où l’utilisatrice ne choisit rien.
- [ ] Couvrir l’expiration et la révocation de l’appairage du relais ainsi que l’affichage
  d’un jeton au périmètre incomplet. Tester l’appairage depuis Réglages avec Playwright.
- [ ] Écrire un test pour une tâche trop longue et un autre pour une semaine pleine. Donner
  le motif au Stratège dans le premier cas et proposer une semaine supplémentaire dans le
  second. Tester l’application explicite de la proposition.
- [ ] Tester la sélection « Hors périmètre » et le choix d’un programme propriétaire pour un
  écart d’offre. Garantir l’isolation sur le programme choisi et conserver le flux D220.
- [ ] Comparer le CV généré à un CV source à jour. Couvrir tous les liens du profil, les faits
  pertinents et les compétences en plusieurs colonnes. Vérifier le rendu PDF avec la source
  de test avant un essai réel.

## 5. Vérifications et clôture

- [ ] Lancer les tests de domaines modifiés, les contrôles de dépendances et de types arrière
  et avant, les contrats et les parcours Playwright (application et connexion). Contrôler
  aussi le choix OpenAI dans un parcours isolé si le modèle peut être appelé.
- [ ] Inscrire les décisions dans `DECISIONS.md` et les preuves dans le bilan. Vérifier le
  diff et l’index, puis créer les commits par chemins et le tag après la recette.
