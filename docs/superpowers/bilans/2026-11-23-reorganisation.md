# Bilan de la réorganisation de Tremplin

Branche locale `codex/reorganisation`, partie de `4c155a1c65dfe10ec7c71bb7d6e3edd02a743e51`.

## Ce qui a changé

- Accueil, Étudier, Coder, Cerveau et Carrière regroupent les usages principaux. Le Labo
  donne accès aux activités secondaires et permet de les épingler. Les anciennes URL
  continuent à ouvrir leurs écrans. Réglages se répartit entre quatre onglets.
- Le Cerveau et Session training utilisent la même liste de conversations. Le titre vient
  de la première question et peut être modifié. Le mode et les leçons d’un training
  sont propres à son fil, avec un maximum de huit leçons. Les anciens fils gardent leurs
  identifiants et leurs messages. Vider ou supprimer un fil d’Étudier conserve les
  fiches, les preuves et la progression déjà enregistrées. Le fil peut continuer après le bilan.
- Le Cerveau indique l’état du relais et la progression par dossier. Les exclusions
  portent sur les sous-dossiers et les extensions. Les réglages de modèles indiquent
  les fournisseurs auxquels il manque une clé.
- Le MCP peut lister, lire, créer, renommer et poursuivre les fils. Pour vider un fil,
  le supprimer, effacer tous les fils d’un espace ou demander la suppression du compte,
  il prépare une confirmation dans Tremplin. `tremplin_overview` indique les rubriques,
  les outils accessibles au jeton et les prérequis.

Voir [l’inventaire des routes et outils](../plans/2026-11-23-reorganisation-inventaire.md)
et [les décisions D296 à D299](../../../DECISIONS.md#d296).

## Contrôles

- Playwright sur Edge avec backend FastAPI et SQLite de recette. Deux parcours réussis
  pour le Cerveau et Étudier. Ils couvrent la réouverture, l’indépendance des modes et
  leçons, le renommage, la recherche, les confirmations et le retour du focus.
- Le test de migration depuis `0071` vérifie la conservation des identifiants, des
  messages et de leur ordre. Les tests d’isolation vérifient qu’un autre compte ne peut
  lire, renommer, vider ou supprimer les fils, et que l’effacement conserve les acquis.
- Une annulation MCP enregistrée avant la migration peut renvoyer un conflit si son
  instantané de ligne ne correspond plus à la conversation migrée. L’historique de la
  conversation et les acquis restent disponibles.

- Deux recettes Playwright de réorganisation ont vérifié les sept accès au menu,
  le parcours clavier, l’ancienne adresse du Cerveau, la persistance des épingles
  et la concordance des 32 cartes du Labo avec le MCP.
- 168 tests Vitest ciblés, dont 22 rejoués après la vérification des groupes.
  12 tests backend sur le Labo et la synchronisation, et 12 tests du relais.
- 88 tests MCP ciblés et quatre tests du notebook ont réussi. Ils couvrent la
  suppression confirmée du compte, son isolation, le lien d’export et la lecture
  du notebook sans modification. Quelques tests backend ont utilisé un délai
  de démarrage plus long pour tenir compte de la charge du poste Windows.
- Le registre MCP compte 408 outils, dont 196 en lecture, 142 en écriture annulable
  et 70 à confirmer. L’inventaire indique les 44 exclusions de niveau 4 et les
  équivalents réservés aux transports. Le décompte inclut les nouveaux outils de
  conversation, de préférences et d’effacement du compte.
- La demande MCP d’acceptation d’une note d’IDE présente l’identifiant de la note.
  Le détail de la proposition apparaît dans l’IDE et l’acceptation vérifie l’empreinte
  du fichier.

- Les contrôles de format, de types, d’imports et de contrat ont été rejoués
  par les hooks Git.

## Captures

- [Menu](2026-11-23-reorganisation/menu.png)
- [Accueil](2026-11-23-reorganisation/accueil.png)
- [Étudier](2026-11-23-reorganisation/etudier.png)
- [Labo](2026-11-23-reorganisation/labo.png)
- [Cerveau sans relais](2026-11-23-reorganisation/cerveau-sans-relais.png)
- [Conversations du Cerveau](2026-11-23-reorganisation/conversations-cerveau.png)
- [Conversations de Session training](2026-11-23-reorganisation/conversations-training.png)

## Ce qui attend January

La mission jointe demande son accord avant la publication sur GitHub et la suite de la
mission. La reconstruction payante des quatre programmes fera l’objet d’une estimation
après le pilote OpenAI. Les vérifications de ce lot utilisent exclusivement des données
et des fournisseurs de test.
