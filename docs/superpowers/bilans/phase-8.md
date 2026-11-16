# Bilan de la phase 8 (Quotidien)

Tag `phase-8`. 19 tâches (8.0 à 8.18), 32 commits depuis `phase-7`.
- **Revues par tâche** : mode économie, Sonnet pour écrire et pour relire. Tâches complexes (8.1, 8.4, 8.9, 8.10) : relecture, un tour de correction, revérification. Tâches simples : relecture puis un tour, sans revérification, seulement s'il y a un Critical ou un Important. La 8.12 a laissé son Important à la 8.15 (même composant). La 8.16 (parcours e2e) est couverte par la revue finale, comme la 7.17.
- **Revue finale** : trois zones en parallèle sur Opus high (back quotidien, back projets, front et e2e). Résultat : 0 Critical, 6 Important, 26 Minor. Une seule vague de 21 correctifs (b6b889c back, a39601c front, D173), revérifiée sur Sonnet. Trois points restants (N1 à N3), dont un touche l'honnêteté du brief, corrigés à part (d1532cf).
- **Tests** : back 5 144 passés à a39601c (passage complet, 39 min, sans test instable) ; après d1532cf, 792 tests des dossiers touchés (brief, radar, graphes) ; front 2 329 (384 fichiers). Parcours Playwright n° 1 à n° 4 réussis sur Edge après la vague (5 passés, 3,0 min).

Contrôle de fin de phase sous Docker, avec GLM réel, SearXNG et Qdrant (script `check_phase8`, parties `planifie`, `radar`, `brief`, `projets` et `tout`) :
- **Essai de milieu de phase (8.8, D164)** : `planifie` ✅ (brief créé par le planificateur 576 s après le réglage, `origin = schedule`) ; `brief` ✅ (1 appel, 0,0004 $) ; `radar` ✅ trois fois (39 à 64 s, 4 à 5 appels, 0,015 à 0,017 $, 29 liens uniques, 11 ou 12 offres analysées, `low_sample`, 2 salaires vérifiés dans leur page).
- **Projets (8.18, D174 n° 5)** : joués sur une **pile jetable** (copie des volumes, conteneurs `learning_career_platform-check8-*` retirés ensuite), à la demande de l'utilisatrice. Deux essais : dépôt lu, évaluation en 10 s, 1 appel, 0,0017 $ et 0,0020 $, verdict `to_redo` (0 critère sur 5 et sur 6), critères nommés, profil inchangé. La voie « validé » n'a pas tourné sur GLM.
- **Essai de clôture (image finale, même pile jetable, brief du jour retiré de la copie, D174 n° 6)** :
  - `tout` deux fois ✅ (12 étapes sur 12, 61 s et 48 s) :
    - radar : 39 s et 33 s, 5 appels, 0,016 $, 13 et 12 offres analysées, `low_sample`, 2 salaires vérifiés dans la page ;
    - brief : conseil prêt en 9 s, 2 appels, 0,0011 $, **ressource trouvée** (correctif de D164) ;
    - projets : `to_redo` (0 sur 5, 0 sur 6), 0,0018 $ et 0,0020 $, profil inchangé.
  - `planifie` ✅ : brief créé seul par le planificateur 190 s après le réglage (`origin = schedule`). Un premier essai avait échoué par ma préparation de la copie : la ligne `jobs` du brief du jour disait la tâche faite. Il faut retirer le brief **et** cette ligne.
  - Journaux relus après coup : aucune donnée. Restent 4 WARNING `search_unavailable` (requêtes `site:` connues) et les deux `ERROR sqlalchemy.pool`.
- **Navigateur, vraie pile, 1 024 px** (image du front reconstruite) : accueil (brief et ses sept rubriques, fil d'activité), radar, Portfolio et page d'un projet. Aucun défilement horizontal, console sans erreur ni avertissement.
- **Poste (hôte Windows)** : depuis le 16/11 à 14 h 36, Smart App Control bloque aussi `backend\.venv\Scripts\python.exe`. Le hook pre-commit local (non versionné) lance le Python signé d'uv avec les paquets du venv, avec l'accord de l'utilisatrice (copie d'origine `.git/hooks/pre-commit.orig`). Les hooks tournent en entier. `pnpm.exe` et le Chromium de Playwright restent bloqués : `node` pour les outils du front, Edge par une config temporaire retirée ensuite. `docker compose build` demande une autorisation de lecture (`--allow=fs.read`) : l'image du front se construit par `docker build` direct.

Décisions : D156 à D174 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Registre des tâches planifiées (`ledger`)** : table `jobs`, réservation, nouvel essai borné, reprise d'une ligne morte, abandon. Tâches complètes : brief 7 h, radar hebdomadaire, bilan, relances, leçons J-7, rafraîchissement ATS tous les 30 jours (reporté de la phase 6), énoncés de projets.
- **Radar du marché (F12)** : graphe `market_radar` (Éclaireur et Analyste). Les requêtes sont écrites par le code, 12 au plus. Plafonds de candidats, de lectures et d'offres lisibles. Classement des compétences avec leur écart au relevé précédent, `low_sample` sous 30 offres, salaires relus dans la page de l'offre. Un relevé par semaine, dû dès le lundi 6 h et rattrapé dans la semaine ; trois essais seulement après un échec. Le modèle est vérifié avant toute recherche (`llm_unavailable`).
- **Brief du jour (F17)** : graphe `daily_brief`. Sept rubriques : bloc du jour, révisions, relances, nouvelles offres, semaine, ressource, conseil en deux phrases. Les nombres du conseil sont contrôlés par le code. Chaque rubrique est isolée : une source en panne donne « Rubrique indisponible ce matin. », jamais une erreur 500, et le conseil n'en parle pas. Un brief par jour, créé à l'heure réglée ou à la première ouverture.
- **Projets (F11)** : graphes `project_brief` (énoncé de 3 à 6 critères) et `project_review` (le Praticien évalue rendu et dépôt). `validated` n'est rangé que si le parcours et le code le disent. Un projet validé produit quatre brouillons (post LinkedIn, entrée du profil maître, README, pitch) ; sans brouillons, l'évaluation est quand même rangée. Il fait passer les compétences du module à `prouve`. L'entrée au profil maître se fait seulement au clic de January, une seule fois.
- **Fil d'activité** : sources isolées, curseur `(at, id)`, noms des agents alignés entre back et front, les captures de January exclues.
- **Front** : accueil (brief, quatre actions rapides, `ActivityFeed`, notices de fond), pages Radar, Portfolio et Projet (rendu, évaluation, brouillons, entrée au profil). Le focus ne retombe plus sur `body` après les actions principales.
- **Bout en bout** : parcours Playwright n° 4 (brief et radar) ; script `check_phase8` (`planifie`, `radar`, `brief`, `projets`, `tout`).
- **Correctifs d'ouverture (8.0)** : les mineurs parqués de la phase 7 (M1 à M8 et front).

## Arbitrages pris pendant l'exécution

- **Organisation** :
  - les implémenteurs ne lancent plus la suite complète (25 à 39 min) ; ils lancent les dossiers concernés, et le contrôleur lance la suite complète en fond après chaque commit back ;
  - un seul écrivain à la fois ; les tours de correction attendent le commit de la tâche en cours ;
  - pas de relecture séparée pour la 8.16 (tests seuls) ;
  - une seule vague de corrections finale, puis un correctif ciblé pour N1 (honnêteté du brief), pas de seconde vague.
- **Radar** :
  - « trois essais par semaine » seulement pour un relevé fini en `failed`, pour qu'il y ait au plus un relevé réussi par semaine ;
  - échantillon de 29 liens accepté : SearXNG renvoie presque les mêmes résultats aux requêtes voisines, et le relevé le dit (`low_sample`).
- **Projets** :
  - l'entrée du profil maître proposée par le Praticien s'affiche comme formulaire (`ProfileEntryForm`), pas comme carte de texte ;
  - le contrôle réel des projets se joue seulement sur une pile jetable (choix de l'utilisatrice) : aucun faux `prouve` ni fausse entrée dans ses données.
- **Script** : l'étape `journaux` lit les journaux passés au lancement, donc d'avant l'essai ; elle est complétée par une relecture à la main après coup.

## Revue finale et corrections

- **Back quotidien** (Opus high) : 0 Critical, 2 Important, 10 Minor.
  - **I1** : « offres lues » comptait les pages qui n'étaient pas des offres. Corrigé : `not_postings` dans le fil et dans le résumé des relevés (contrat régénéré).
  - **I2** : le radar hebdomadaire n'était dû que le lundi, sans rattrapage. Corrigé : dû dès le lundi 6 h, une fois par semaine.
  - Minor corrigés : M1 à M7 (titre d'abandon, date d'une ligne reprise, modèle vérifié avant la recherche, lot de l'Analyste en panne, « tâches », isolation par rubrique, date des leçons) et M9 (attentes de tests instables).
- **Back projets** (Opus high) : 0 Critical, 2 Important, 6 Minor.
  - **I1** : un index hors bornes pouvait ranger `validated` alors que le parcours disait `to_redo`. Corrigé.
  - **I2** : un échec des brouillons faisait perdre l'évaluation validée. Corrigé (délai propre, « brouillons indisponibles », D165 n° 5).
  - Minor corrigés : M1 à M4 (champs du modèle nettoyés, critères sur une ligne, doublon de `verdict` retiré, trois énoncés par passage).
- **Front et e2e** (Opus high) : 0 Critical, 2 Important, 10 Minor.
  - **I1** : le focus tombait sur `body` après « Enregistrer », « Rendre le projet », « Ajouter au profil maître », « Réessayer l'énoncé », « Lancer un relevé » et une relance en échec. Corrigé, un test par cas.
  - **I2** : même compte « offres lues » côté front. Corrigé.
  - Minor corrigés : conseil relu à intervalle borné, Entrée dans « Nom du projet » sans ajout implicite, `aria-busy`, `h1` des états de chargement et d'erreur, libellé du télétravail, arrivée du conseil annoncée, erreur d'un brouillon sur sa carte.
- **Revérification** (Sonnet) : les 21 points traités. Points nouveaux : N1 (une rubrique en panne restait vide et le conseil pouvait s'en servir), N2 (un relevé sans offre analysée finissait `done`), N3 ; corrigés en d1532cf. N4 et N5 parqués.

## Points laissés pour plus tard

### À vérifier en réel
- Reportés de la phase 5, toujours dus : `valide` par un quiz réussi au nouvel essai ; tâches cochées par une séance ou un quiz ; bilan hebdomadaire en relançant `check_phase5` le dimanche 22/11.
- Voie « validé » d'un projet sur GLM (brouillons, `prouve`, entrée au profil) : couverte par les tests et `test_live.py`, pas encore par un essai réel.
- Entretien blanc et comité (phase 7) : pas encore d'essai réel GLM.
- Premier vrai CV et première vraie offre de January.

### Phase 9 — correctifs d'ouverture
- Étape `journaux` de `check_phase8` : relire les journaux **après** l'essai, pas ceux passés au lancement.
- Deux `ERROR sqlalchemy.pool … Exception terminating connection` (aiosqlite à la fermeture d'une connexion) vus sur la pile jetable.
- N4 : le focus du radar lit `location.state`. N5 : `retried` n'est jamais remis à zéro.
- Aucun moyen de régénérer les brouillons d'un projet validé qui n'en a pas (« brouillons indisponibles »).
- A-M8 de la revue finale ; hypothèse du parcours e2e « aucun parcours n'a ouvert l'accueil avant » ; formulaire « à reprendre » non prérempli ; docstring de `tests/e2e/server.py`.

### Radar
- Élargir l'échantillon : clé Brave ou page 2 de SearXNG (port `WebGateway.search`, clé du cache, trois fournisseurs).

### Mineurs parqués des revues par tâche (détail dans les revues)
- 8.9 : pas de test de reprise autour de `redo` ; `redo` sans garde sur `found` vide à la reprise ; toute `TimeoutError` du fournisseur prise pour un délai du nœud.
- 8.10 : M2, M4, M5, M8 à M10 ; `FormRoute` lit le texte du message Starlette et nomme toujours `description` ; crochet `in_transaction` du CV non testé ; un JPEG nu de 4 octets accepté.
- 8.11 : M3 à M6.
- 8.12 : M6.
- 8.13 : notices de rattrapage en rafale ; notice de 8 s sans pause ; ordre de la fenêtre `after`.
- 8.14 : M4, M6.
- 8.15 : M2, M4.

### Outillage et poste
- `pnpm.exe`, le Chromium de Playwright et le lanceur du venv bloqués par le contrôle d'applications ; hook pointé vers le Python signé d'uv (à refaire si `pre-commit install` est relancé).
- Les hooks back demandent le shim `uv` sur le PATH.
- `docker compose build` demande `--allow=fs.read=…` : construire l'image par `docker build` direct.
