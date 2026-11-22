# Phase 19 · Recette Edge

22 novembre 2026. Playwright a validé le parcours `frontend/e2e/contributions.spec.ts`
sur Edge (1 test, 11,8 s pour le scénario). Le scénario a utilisé Vite et l’API Tremplin
sur une base SQLite éphémère avec des données fictives.

- Le programme de recette propose l’issue pandas du dépôt étudié et écarte l’issue numpy.
- Le dossier garde le lien de publication inaccessible avant la confirmation. Après confirmation
  au clavier, un onglet GitHub simulé reçoit les branches, le titre, le texte et le repère de suivi.
- Le dossier suit une PR ouverte sans proposer de ligne pour le CV. Après la fusion simulée, un
  clic sur « Actualiser son statut » affiche la contribution acceptée et la proposition de ligne CV.
  L’API de la carte confirme le niveau « prouvé » et une seule preuve, liée au dossier.

Le serveur répond aux lectures GitHub via `FakeFetcher`. Playwright intercepte toute navigation
vers GitHub dans le contexte de recette. La vérification a rejoué ce seul parcours.
