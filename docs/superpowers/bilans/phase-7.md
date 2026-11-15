# Bilan de la phase 7 (Candidatures)

Tag `phase-7`. 20 tâches (7.0 à 7.19), 41 commits depuis `phase-6`.
- **Revues par tâche** : en mode économie, sur Sonnet sauf 7.0 et 7.1 (Opus high). Tâches complexes (7.1 contrat d'honnêteté, 7.4, 7.5, 7.8, 7.10 graphes LangGraph) : relecture, un tour de correction, revérification. Tâches simples : relecture puis un tour, sans revérification. Au total 2 Critical (7.1) et 7 Important, tous corrigés. La 7.7 (essai réel) et la 7.17 (parcours e2e) sont couvertes par la revue finale.
- **Revue finale** : back et front en parallèle sur Opus high (phase-6..2de8033). Une seule vague de corrections (e38c14f à d273973, D155), revérifiée sur Sonnet : propre, 0 Critical et 0 Important.
- **Tests** : back 4 486 passés, plus un test au timing connu (`test_web_research_replay`) vert seul ; les 7 tests corrigés en fin de vague relancés par dossier (1 810 passés), pas par un second passage complet ; front 2 002 (335 fichiers) ; parcours Playwright n° 1, n° 2 et n° 3 réussis sur Edge après la vague de corrections.

Contrôle de fin de phase sous Docker, avec GLM 5.3 flash, SearXNG et Gotenberg réels (script `check_phase7`, parties `suivi` et `kit`) :
- **Essais de la 7.7** : `suivi` deux fois (5 s et 4 s, saisie en une phrase en 1 appel, 0,0008 $) ; `kit` deux fois (36 s, 9 appels, 0,0145 $ ; 13 s, 8 appels, 0,0095 $). Aucun drapeau d'honnêteté, aucune correction du back.
- **Essais de clôture (image reconstruite après la vague de corrections)** :
  - `suivi` : 6 étapes sur 6 en 4 s. Doublons à trois niveaux (même lien 409 certain, intitulé « (H/F) » 409 probable, autre poste en information). Phrase lue en 2 s et 1 appel (0,0008 $), fiche postulée la veille par LinkedIn. Relance J+7 due avec brouillon (55 mots), reportée puis faite, fiche « Relancée ». Indicateurs : 8 fiches.
  - `kit` : 3 étapes sur 3. 7 pièces en 15 s, 6 appels, 0,0075 $ (11 041 tokens). 5 pièces prêtes et 2 à vérifier. La lettre fait 271 mots. Le dossier repris garde « à vérifier » (correctif M2 vu en réel), avec 4 sources. `kit.zip` lisible (9 fichiers).
  - Journaux du back : relus sans entreprise, intitulé, contact, phrase, brouillon, contenu de CV, URL ni nom de fichier `CV_`.
- **Poste (hôte Windows)** : comme en phase 6, `pnpm.exe` et le Chromium de Playwright restent bloqués. Les hooks passent par `node`, et Playwright tourne avec Edge par une config temporaire, retirée ensuite.

Décisions : D137 à D155 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Suivi des candidatures (F5)** :
  - fiches, statuts, Kanban (souris et clavier), fil d'événements ;
  - doublons à trois niveaux, information « même entreprise depuis 30 jours » ;
  - fiche créée depuis une offre, à la main, ou en une phrase (graphe `application_intake`, carte de confirmation, rien d'écrit sans « Tu valides ? ») ;
  - relances J+7 et J+14 avec brouillon, report, « Fait » ; délais réglables ; indicateurs (taux de réponse, délai moyen) et badge dans la navigation ;
  - une fiche sans offre peut recevoir le texte de l'offre plus tard (D155).
- **Kit de candidature (F16)** : graphe `application_kit` en parallèle, 7 pièces (CV ciblé, lettre, messages LinkedIn, relances, réponses aux questions de formulaire, pitch de 60 s, dossier entreprise sourcé). Contrôle des faits par le code, un seul nouvel essai, puis « à vérifier » avec les termes en cause. Réponse de salaire toujours laissée à January. Pièces modifiables, gardées à la relance. Archive `kit.zip`.
- **Entretien blanc (F10)** : graphe `interview` (une question à la fois, relances, arrêt), débrief noté, cartes de révision. Les réponses sont gardées même quand le débrief échoue (`debrief_failed`).
- **Comité d'embauche (F19)** : graphe `hiring_committee`, 4 personas (Lecteur ATS, Recruteur, Manager, Collègue) et un modérateur. Ordre de parole fixé par le code, 17 tours de modèle au plus. Verdict à la majorité absolue, sinon « peut-être ». Changements conseillés contrôlés par le profil (un nom propre absent devient « À vérifier », D155).
- **Front** : pages Suivi, nouvelle fiche, tiroir d'une fiche, Kit, Entretien blanc (liste, séance, débrief), Comité ; `useRun`, `RunFeed` et `SideTabs` partagés dans `shared/`.
- **Bout en bout** : parcours Playwright n° 3 (cycle de candidature), script `check_phase7` (parties `suivi` et `kit`).
- **Correctifs d'ouverture (7.0)** : I-D, I-E, libellé des `gap_terms`, carte « Tu valides ? » retirée, et les mineurs parqués de la phase 6.

## Arbitrages pris pendant l'exécution

- **Organisation** :
  - mode économie renforcé dès le matin du 15/11 : une relecture Sonnet par tâche, deux pour une tâche complexe, Opus high seulement pour la revue finale ;
  - aucun front en parallèle d'un écrivain back dans le même arbre (le stash du hook mélange les fichiers non commités) ;
  - le tour de correction de la 7.12 est intégré à la 7.13 (même dossier, implémenteur arrêté) ;
  - la revue finale lancée sans attendre la remise à zéro du mardi (« pousser un max sur la limite »).
- **Honnêteté (`text_claims`)** :
  - les nombres de référence sont ceux des textes des faits et les années des dates, jamais le téléphone, l'email, une URL ou un mois ;
  - `allowed` ne contient que des phrases entières (entreprise, intitulé exact, nom du contact), jamais les termes de l'offre ;
  - l'intitulé de l'offre n'est retiré que dans un contexte de destinataire (« votre poste de… »), pas après un indice de soi (« mon poste de… ») ;
  - un mot tout en capitales n'est jamais sauté ; « may » en minuscules n'est pas un mois.
- **Saisie en une phrase** : avec une alerte de doublon, les choix sont distinct, ouvrir ou annuler, jamais « créer » ; les champs modifiés gardent les alertes d'origine.
- **Kit** : limites de mots sur toutes les pièces avec le même essai unique ; un `PATCH` d'une pièce ne revérifie ni le CV, ni le dossier, ni les questions, ni le salaire ; un kit en cours ne bloque pas l'édition.
- **Entretien** : le code tranche le point le plus faible et les manques à partir des notes internes ; arrêt sans débrief = `stopped`.
- **Comité** : majorité absolue (3 sur 4), sinon « peut-être » ; le plafond de 17 compte les tours de modèle (les nouveaux essais de `structured_call` peuvent le dépasser, le plafond de tokens borne le coût).
- **Adoption (D155)** : une offre qui ressemble à une fiche déjà liée à une autre offre, ou « possible », ne crée aucune fiche ; l'alerte de la page de l'offre reste le chemin.

## Revue finale et corrections

- **Back** (Opus high) : 0 Critical, 2 Important, 8 Minor.
  - **I1** : une fiche créée sans offre ne pouvait jamais en recevoir une (kit bloqué), et coller l'offre plus tard créait une seconde fiche. Corrigé : `PATCH` accepte `posting_text`, l'adoption relie la fiche sans offre (`adopt_link.py`), contrat régénéré.
  - **I2** : les changements du comité ignoraient les noms propres (« Mets en avant ton expérience chez Capgemini » passait). Corrigé : seuls les mots de section d'un CV sont exclus, un employeur ou une école absents du profil donnent « À vérifier ».
  - **M2** : un dossier repris passait « prêt » malgré des sections vidées. Corrigé (`check_dossier`, vu en réel).
  - **M4** : l'information « même entreprise » n'arrivait jamais par une phrase. Corrigée (`intake_info`, champ `info` de `artifact.ready`, note dans le tiroir).
- **Front** (Opus high) : prêt à taguer, 0 Critical et 0 Important, 12 Minor dont 4 corrigés : cache relu après une création hors des hooks, dates futures refusées (`max` = aujourd'hui), score manquant « non noté » et non « 0 sur 5 », note « tu le suis ici » retirée à la fin d'une exécution reprise. En plus : « Ajouter le texte de l'offre » dans le tiroir, vers lequel pointe le message `posting_required` du kit.
- **Revérification** (Sonnet) : les 9 points corrigés, écarts acceptés, 6 Minor nouveaux (voir plus bas).

## Points laissés pour plus tard

### À vérifier en réel
- Reportés de la phase 5, toujours dus : `valide` par un quiz réussi au nouvel essai ; tâches cochées par une séance ou un quiz dès le lundi 16/11 ; bilan hebdomadaire en relançant `check_phase5` le dimanche 22/11.
- Entretien blanc et comité : couverts par les tests et le parcours n° 3 (modèles scriptés), pas encore par un essai réel GLM.
- Premier vrai CV et première vraie offre de January : tous les essais réels portent sur le profil fictif.

### Phase 8 — mineurs de la revue finale (D155, n° 6)
- **M1** : la pièce `cv` du kit prend la dernière version prête, pas la version envoyée.
- **M3** : le séparateur des relances (« --- ») n'a pas la même règle côté graphe et côté route.
- **M5** : les valeurs des votes du comité sont journalisées.
- **M6** : la suppression d'une offre ne voit ni le comité ni l'entretien libre en cours (lignes orphelines).
- **M7** : deux verrous différents protègent la création de la fiche entreprise.
- **M8** : `EventIn.on` accepte une date future côté back.
- Front : niveaux de titres incohérents, boutons de relance actifs pendant l'action, `ChangeList` redondant, cast qui contourne le typage, pas de `maxLength` sur entreprise et intitulé, clés React par texte, exception `*Testkit` trop large, le Kanban défile à 1 024 px, la raison de relance de l'intake perdue au rechargement.

### Mineurs de la revérification
- `adopt_link.target_of` peut relier une fiche « probable » sans offre alors qu'un hit « certain » vise une fiche liée à une autre offre (rare).
- Relier une fiche déjà postulée fige la version et écrit « Version N du CV envoyée. », alors que la version peut être postérieure à la candidature saisie à la main.
- `intake_info` est lu avant l'écriture : une erreur de lecture de l'information empêche la création de la fiche ; l'envelopper (info vide et journal sans contenu).
- `IntakeRun` : l'effet d'invalidation dépend d'un objet recréé à chaque événement (sans effet visible aujourd'hui).
- `SECTION_WORDS` du comité incomplet (Certifications, Intérêts, Loisirs…) : faux « À vérifier », sens sûr.
- Docstring de `adopt.py` muet sur le lien des fiches sans offre.
- Noms d'entreprise non latins (`company_key` vide) : un intitulé proche à 85 % suffit à relier une fiche d'une autre entreprise non latine.
- Date de la machine contre date de January : le contrôle de date future côté client compare à la date du navigateur, le serveur au fuseau de réglage (écart d'un jour possible).

### Mineurs parqués des revues par tâche (détail dans les revues)
- Écritures sans espaces (japonais d'un seul tenant) : un nom correct peut être redemandé.
- `to_apply` avec une date future coûte un tour de modèle de plus ; champ fait d'espaces seuls envoyé au chemin vide.
- `artifact.ready` perdu au redémarrage (la pièce est enregistrée, la page la relit par l'API).
- `except BaseException` puis commit dans `_launch` de l'entretien (la lecture marque `failed`).
- Relance d'entretien sans note laisse `unrated` faux ; « débrief s'écrit » peut s'afficher quelques secondes trop tôt ; entretien libre sur une offre non prête sans nom.
- Nom accessible du badge « Relances , 1 relance due » (espace avant la virgule).
- Raison d'une nouvelle question de l'intake devinée côté client (le serveur n'en donne pas).

### Phase 8
- Rafraîchissement de la base de connaissance ATS tous les 30 jours (reporté de la phase 6).

### Outillage et poste
- `pnpm.exe` et le Chromium de Playwright bloqués par le contrôle d'applications ; Edge par config temporaire.
- Les hooks back demandent le shim `uv` sur le PATH : sans lui, import-linter et `export_openapi` échouent (DLL du `.venv` bloquées).
- Test au timing fragile : `test_web_research_replay::test_judge_stopped_midway…` ; `test_pieces_are_announced_as_they_finish` a échoué une fois dans un passage `-x`, vert seul.
