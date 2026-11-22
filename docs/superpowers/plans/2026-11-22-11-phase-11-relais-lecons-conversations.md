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
- La reconstruction des quatre programmes est reportée après la phase 43 (D227). La recette
  longue des clients MCP est soumise à l’accord de coût du plan directeur.

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
- [x] Tester l’application de la même validation au Rédacteur et aux écritures directes.
  Déclencher la Fabrique avec le brouillon fourni et garder la version publiée précédente
  jusqu’à publication de la nouvelle. Tester les refus avec raisons, la vérification qui
  redemande une révision et l’ajout de ressources seul sur un chapitre historique (D221).
- [x] Ajouter la grille structurée à `agents/nodes/verifier`. Tester qu’un vérificateur
  refuse un critère sous le seuil même si la moyenne passe. Conserver le contrôle des sources.
- [x] Tester qu’un prérequis non introduit dans un chapitre précédent est rendu au Stratège
  et que le glossaire et les chapitres voisins arrivent dans le brief. Préserver la lecture
  des anciens instantanés.
- [x] Vérifier sur le pilote que le premier chapitre pose bien les fondations.
- [x] Orienter les nouvelles leçons vers la Fabrique dans le guide et les consignes MCP.
  Adapter les réponses scriptées à la nouvelle grille.
- [ ] Vérifier le brief et la norme pendant la recette réelle avec le client MCP.
- [x] Générer deux ou trois chapitres LangChain en pilote sur la pile jetable. Contrôler la
  structure, les sources, les notes du Vérificateur et le coût avant de présenter le résultat.

## 3. Conversations partagées

- [x] Extraire la saisie, le fil et les messages de l’IDE dans `shared/ui`. Garder dans l’IDE
  les actions rapides, cartes de proposition et renvois au code. Vérifier la réutilisation
  avec une conversation qui possède ses propres libellés et liens de sources.
- [x] Tester dans une nouvelle feature `conversations` la persistance d’un fil et des sources,
  l’isolation entre comptes, une reprise sans doublon et un dépassement de budget. Réutiliser
  les sessions et fournisseurs existants pour lancer la réponse sans bloquer la requête.
  Commencer par le Professeur. Le fil est unique par compte et leçon publiée. Un identifiant
  créé par l’interface rend la soumission d’un tour idempotente. La réservation du tour et la
  session sont enregistrées dans la même transaction. Le graphe reçoit les identifiants du fil
  et du tour, relit le passage, les derniers échanges et les extraits via les ports. Les sources
  structurées sont choisies dans les références de ce tour et stockées avec la réponse. Le flux
  de session existant signale l’avancement et l’interface recharge le fil à la fin du tour.
  Le sélecteur annonce l’intervalle de relève de deux minutes retenu dans D222.
  Couvrir le modèle léger, la demande explicite d’un modèle fort et l’état du budget avant de
  brancher les deux autres portes. Verrouiller le parcours derrière sa route et son outil MCP.
- [x] Partager les briques du chat IDE. Ajouter le panneau du professeur au lecteur, lié à la
  leçon et au passage courant. Tester au clavier le retour du focus et la réouverture du fil.
- [x] Relier le training au suivi d’étude. Tester les trois modes, leur changement pendant le
  fil, l’exclusivité avec une séance guidée et l’enregistrement des fiches et preuves sans
  cocher de tâche planifiée.
  Les séances restent dans `study_sessions`. Distinguer bloc guidé et training par leur type et
  conserver le même index `uq_study_sessions_open`. Une séance training ne reçoit ni leçon ni
  bloc imposés au départ. Son fil reprend l’identifiant de séance. À la fin, déduire les modules
  et fiches des leçons citées au fil, valider leur appartenance et inscrire le temps et le journal
  par le service d’étude. Tester un rejeu de clôture pour chaque effet enregistré.
- [x] Relier Cerveau à la mémoire. Tester le remplacement et le retrait des extraits, la
  reprise après une coupure et l’ignorance des jonctions et dossiers techniques. Réutiliser
  les contrôles d’ingestion, lier chaque fichier à son dossier et réserver la gestion des
  chemins au compte connecté. Le relais envoie les fichiers autorisés sous un jeton distinct.
  Commencer par la gestion de dossiers et un scanner du relais testable hors ligne. Sur le
  serveur, garder dossier, chemin relatif validé, empreinte et état de sa dernière ingestion.
  Un retrait est traité comme un retrait de document de mémoire afin que ses extraits cessent
  d’apparaître aussi dans les recherches des agents. Relier le chat après ces vérifications.
- [x] Déclarer les entrées MCP et ajouter les tests Playwright du professeur, du training et
  d’une note retrouvée puis retirée. Vérifier que les liens de sources ouvrent le bon document.

## 4. Reports de la phase 10b

- [x] Tester les choix fournisseur par lancement et l’héritage dans les reprises et sessions
  enfants. Conserver le réglage global pour les lancements où l’utilisatrice ne choisit rien.
- [x] Couvrir l’expiration et la révocation de l’appairage du relais ainsi que l’affichage
  d’un jeton au périmètre incomplet. Tester l’appairage depuis Réglages avec Playwright.
  Le compte connecté crée un code temporaire à usage unique. Le navigateur le transmet au
  relais local, qui échange le code contre un jeton dédié et l’enregistre. Le relais local
  accepte la requête des origines configurées et échange le code auprès de son API configurée.
  La tentative et le renouvellement apparaissent dans Accès MCP. Seuls le code de l’état et
  les portées manquantes sont affichés après l’appairage.
- [x] Écrire un test pour une tâche trop longue et un autre pour une semaine pleine. Donner
  le motif au Stratège dans le premier cas et proposer une semaine supplémentaire dans le
  second. Tester l’application explicite de la proposition.
- [x] Tester la sélection « Hors périmètre » et le choix d’un programme propriétaire pour un
  écart d’offre. Garantir l’isolation sur le programme choisi et conserver le flux D220.
- [x] Comparer le CV généré à un CV source à jour. Couvrir tous les liens du profil, les faits
  pertinents et les compétences en plusieurs colonnes. Vérifier le rendu PDF avec la source
  de test avant un essai réel.

## 5. Vérifications et clôture

- [x] Lancer les tests de domaines modifiés, les contrôles de dépendances et de types arrière
  et avant, les contrats et les parcours Playwright (application et connexion). Contrôler
  aussi le choix OpenAI dans un parcours isolé si le modèle peut être appelé.
- [x] Inscrire les décisions dans `DECISIONS.md` et les preuves dans le bilan. Vérifier le
  diff et l’index, puis créer les commits par chemins et poser le tag après la recette.
  Les commits et le tag restent locaux jusqu’au prochain jalon de push (D231).
