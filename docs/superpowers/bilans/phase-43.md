# Phase 43 · Site portfolio

La sélection démarre vide. Elle propose le nom, le titre, la présentation, les
compétences et les projets du profil validé, ainsi que les projets terminés,
les preuves GitHub vérifiées et les textes LinkedIn relus sans signalement.
Les champs d’identité réservés au contact restent hors des choix.

Le HTML échappe les champs et utilise une feuille de style intégrée. L’aperçu
et le ZIP privé contiennent le même fichier. Le service affiche l’URL et
l’empreinte avant l’accord explicite. Le remplacement ouvre une nouvelle
version à approuver et le retrait coupe l’accès public suivant. L’URL reste
la même pour les remplacements sur un même hébergement. Deux actions distinctes
ajoutent le lien aux nouveaux CV ciblés ou à `08_portfolio.txt` dans les
archives du kit. Un remplacement ou un retrait réinitialise ces choix.

## Hébergement

`PORTFOLIO_PUBLIC_ORIGIN` reste vide par défaut. Une origine HTTPS distincte
de l’application permet de configurer le site public. Le proxy transmet le
`Host` configuré et ne publie que les requêtes GET sur
`/api/v1/public/portfolios/`. L’API filtre aussi cet hôte et ferme ses WebSockets.
L’accès à la pile privée reste sur son adresse habituelle.

Les fichiers restent dans `FileStorage` par compte. Le site sert uniquement
la version pointée par l’accord enregistré et relit son empreinte. Les anciennes
versions restent dans le stockage privé. Aucun hébergement réel n’a été activé
pendant la recette.

## Vérification

Le scénario Edge sur hôtes locaux a exclu un détail privé de l’aperçu, constaté
le 404 avant l’accord, suivi l’usage proposé pour le CV puis constaté le retrait.
Les tests ciblés couvrent l’isolation, le ZIP, l’empreinte, le remplacement
et l’arrivée du lien autorisé dans le CV ciblé et dans l’archive du kit.
