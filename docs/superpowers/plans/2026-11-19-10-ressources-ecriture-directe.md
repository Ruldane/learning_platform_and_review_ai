# Ressources des leçons écrites directement

> Exécution avec `superpowers:executing-plans`, par étapes cochées après vérification.

**Objectif.** Rattacher des lectures à une leçon créée ou retouchée par le MCP. Elles apparaissent dans les fiches Ressources et dans la Bibliothèque, où January peut changer leur statut.

**Architecture.** Les corps de `lessons_write_lesson` et `lessons_update_lesson` acceptent une liste facultative. Le service rattache les nouvelles fiches au module dans la transaction de la leçon. Il réutilise les lignes existantes et leur statut par URL normalisée. La feature dispose déjà du modèle, du dépôt et des composants de lecture.

**Cadre.** Phase 10.W, écriture directe de niveau 2 et annulable. Aucun téléchargement ni lancement d'agent. `SPEC.md` §3.6 définit les fiches et leur suivi.

## API et persistance

- [x] Écrire et faire échouer des tests MCP pour la création avec ressources, l'ajout à une leçon prête, un deuxième appel avec la même URL et l'annulation. Vérifier qu'une ressource lue conserve son statut et que les fiches apparaissent dans la Bibliothèque.
- [x] Valider une liste bornée de fiches HTTP(S) sans identifiants. Chaque fiche contient un titre, un type, une URL et une raison de lecture. Autoriser les métadonnées facultatives affichées par les fiches existantes.
- [x] Ajouter les nouvelles lignes par `ResourceRepository` sous le verrou existant de la leçon. Préserver les lignes déjà présentes. Vérifier qu'un ajout seul conserve le Markdown et le PDF et que les sorties MCP marquent le texte de ressources comme non fiable.
- [x] Vérifier l'isolation et le rejet d'une URL invalide. Régénérer OpenAPI puis les types du front. Rejouer les tests leçons et MCP concernés.

## Publication

- [x] Vérifier que le serveur local accepte le champ à la création et sur une leçon existante. Rattacher les lectures lors de la publication des cours longs.
- [x] Relire les fiches depuis le MCP et vérifier leur rendu et leur bouton de suivi avec les tests du lecteur. Les tests de changement de statut utilisent des données de test.
