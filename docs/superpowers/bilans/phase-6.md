# Bilan de la phase 6 (CV)

Tag `phase-6`. 20 tâches, 41 commits depuis `phase-5`.
- **Revues par tâche** : 13 tâches à risque revues (6.1 à 6.10, 6.12 à 6.14), d'abord sur Opus high, puis sur Sonnet pour les tâches moyennes à partir de 6.9 (mode économie) ; Opus high est resté pour le contrat, les graphes LangGraph complexes et la revue finale. Au total 0 Critical et 29 Important, tous corrigés. Seule la 6.6 n'a demandé aucun round ; la 6.4 et la 6.12 en ont demandé deux. La 6.11 (essai réel) et les tâches front 6.15 à 6.19 sont couvertes par la revue finale.
- **Revue finale** : back en trois zones (agents, CV, offres et reste), front en deux zones (CV, offres et reste), sur Opus high. Une vague de corrections par côté (a8ac392), une re-revue de chacune, puis deux rounds ciblés sur les corrections de honnêteté restées ouvertes (850fe91, 853e611).
- **Tests** : back 3 869 passés, front 1 609, parcours Playwright n° 1 et n° 2 réussis.

Contrôle de fin de phase sous Docker, avec GLM 5.3 flash, SearXNG, Gotenberg, Ollama et Qdrant réels (script `check_phase6`, 12 étapes, partie `tout`) :
- **Essai de la capture (6.11)** : 6 étapes sur 6 deux fois, dont une avec `--fresh`. Profil en 17 s (0,002 $), design en trois passes de 27 à 37 s (0,008 $, ressemblance de 69 à 77 %), offre analysée en 22 s (0,005 $), second envoi du même texte en 200. Seuil de doublon à 0,90 : bien placé (un autre poste crée une offre, une copie réécrite est signalée « possible »). « 5 ans » contre « cinq ans » : aucun retrait faux sur quatre imports.
- **1er essai du contrôle complet (6.20)** : échec à l'étape 7, sans conséquence. La règle « aucune modification acceptée ne contient un terme de l'écart » était trop stricte : le modèle avait rangé à l'écart « agents » et « support », que le résumé du profil porte réellement. **Corrigé** dans le script : la règle ne vise que les termes absents de tout le profil. L'imprécision du contrat de `gap_terms` reste (voir 7.0).
- **2 essais réels `--part tout`** : 12 étapes sur 12 chacun, sans aucun avertissement. Durées 85 s et 95 s, dont 79 s et 90 s pour la revue.
  - Revue : 16 puis 14 modifications (6 puis 3 « à confirmer »), 3 termes vers l'écart, couverture d'origine 40 %. Coût 0,018 $ puis 0,023 $ (26 700 et 35 900 tokens).
  - Génération : version prête en 1 s, 1 page comme l'original, 5 contrôles ATS sur 5, couverture 40 % → 40 % (les exigences qui manquent, RAG et 3 ans, ne sont pas dans le profil : normal). Au 2e essai, une décision acceptée mais non placée est rendue `ignored`, jamais montrée comme appliquée.
  - Double génération : un 202 et un 409 (`generation_in_progress`). Terminer : revue `done`, puis 409 `review_closed`.
  - Journaux du back : 511 puis 888 lignes relues, sans nom, email, téléphone, entreprise, phrase de l'offre, police ni nom de fichier `CV_`.
- **Conteneur éphémère** : `scripts/` est exclu de l'image du back (`.dockerignore`), donc `docker compose exec backend python -m scripts.check_phase6` ne marche pas. Le script tourne dans un conteneur jetable de la même image, sur le réseau de la pile, dépôt monté, journaux du back en entrée standard. Le docstring le dit.
- **Variabilité du modèle** : pour la même offre et le même profil, l'écart est passé de 12 lignes (6 à ajouter) à 15 (9 à ajouter) entre deux analyses réelles. Rien d'anormal : l'écart se recalcule au lancement et GLM ne répond pas deux fois pareil.
- **Navigateur** : parcours n° 1 (1,6 min) et n° 2 (19,7 s) réussis. Les 9 pages Carrière sur la vraie pile, à 1 024 px : aucun défilement horizontal, aucune erreur de console, aucune réponse HTTP en erreur (comparaison à superposition du gabarit incluse). PDF de la version 6 : 200, 14 490 octets, 1 page comme l'original, nom `CV_<Nom>_<Entreprise>_<Poste>.pdf`. L'image de la page relue : design reconnaissable (bandeau bleu, colonne latérale grise, colonne principale).
- **Poste (hôte Windows)** : le contrôle d'applications (Device Guard) bloque `pnpm.exe` et le Chromium livré avec Playwright. Les hooks du front passent par `node frontend/scripts/run-tool.mjs` (D134), et Playwright a tourné avec Edge par un fichier de config temporaire, retiré ensuite. La config commitée garde Chromium et reste juste sur un poste normal.

Décisions : D117 à D136 dans `DECISIONS.md`.

## Ce que la phase apporte

- **Profil maître** :
  - tables de la carrière, faits à identifiant stable attribué par le code, sources par ligne (CV, LinkedIn, note, January) ;
  - extraction par l'Archiviste (mode `profile`) depuis le CV PDF, LinkedIn et un texte libre ;
  - brouillon relu par January, versions, ré-import qui garde ses faits confirmés ;
  - formulaire du profil, « Utiliser le CV de mon profil » pour créer un modèle.
- **Capture du design (Maquettiste)** :
  - mise en page et images d'un CV en sous-processus, lecture machine, pièges d'invisibilité écartés ;
  - gabarit HTML, score de ressemblance, trois passes au plus, meilleure passe gardée ;
  - polices libres, écarts de polices dits ;
  - comparaison côte à côte et en superposition, « Ajuster » avec consigne.
- **Offres et écarts** :
  - offre par lien ou texte, doublons à trois niveaux, Analyste et parcours `gap_analysis` ;
  - score de match, tableau d'écarts, « Ajouter au planning » (via le Stratège), offres d'une compétence, comparaison à une offre ;
  - suppression d'offre sûre.
- **Revue de CV (`cv_review`)** :
  - Lecteur ATS, Recruteur et Éclaireur (fiche entreprise gardée 30 jours, ATS détecté par le lien de candidature, base ATS datée) ;
  - confrontation en deux tours au plus, puis validateur : un chiffre, un outil ou un titre absent du profil passe en « à confirmer », un mot clé absent part vers l'écart, aucune garantie de passage ATS ;
  - décisions de January une par une, « Tout accepter » qui laisse les « à confirmer ».
- **Génération** : une version par clic, décisions figées au clic, PDF réel (Gotenberg), nombre de pages comme l'original, contrôles ATS, couverture avant et après, versions téléchargeables, nom de fichier normé.
- **Front** : pages Profil, CV (modèles, revue, versions), Offres, Écarts ; section « Carrière » de la navigation ; Maquettiste remplace Designer dans l'interface.
- **Bout en bout** : parcours Playwright n° 2 (revue complète d'un CV, modèles scriptés des six agents, rendu PDF textuel), script `check_phase6` (12 étapes, parties `capture`, `revue` et `tout`).
- **Reliquat de la phase 5** : tokens d'un appel coupé comptés (D117), test `QuizPage` stabilisé, Playwright qui s'arrête seul après un serveur lancé par Docker.

## Arbitrages pris pendant l'exécution

- **Organisation** :
  - mode allégé puis mode économie : revue par tâche seulement pour les tâches à risque, Sonnet pour l'implémentation ordinaire et les revues moyennes, revue finale complète sur Opus high ;
  - un seul écrivain back à la fois ; aucun commit d'un agent pendant que les fichiers d'un autre ne sont pas commités (le stash du hook casse les fichiers non suivis) ; seule la tâche back écrit dans `DECISIONS.md` en parallèle, le contrôleur recopie les décisions des tâches front ;
  - plage légère le soir et pause demandée pendant l'attente du quota : aucun agent lourd, tâches reprises ensuite dans l'ordre ;
  - pré-vol : 35 points de conflit (G1 à G35) tranchés avant la 1re tâche ; le rendu du texte et la taille de page déplacés de 6.19 à 6.4.
- **Honnêteté du CV (le cœur de la phase)** :
  - un fait n'est rangé « note » que si la note le soutient par la même règle de recouvrement que les documents, sinon il est demandé en confirmation (6.8) ;
  - approximations en lettres lues comme des chiffres ; termes ambigus (« vue », « spring », « rest »…) comptés comme outils seulement sous leur forme de produit, liste limitée à 17 mots réels après une re-revue (6.12) ;
  - un fait structuré réécrit (intitulé, diplôme, niveau de langue, lien, compétence) doit reprendre tous ses mots du seul fait visé, ou il passe en « à confirmer » ; les rôles et titres du profil ne comptent que pour un titre (revue finale, résiduel) ;
  - une proposition retirée par son auteur au second tour est retirée ; l'auteur voit son texte d'origine (6.13) ;
  - confirmer un fait est refusé tant qu'un brouillon du profil attend (409 `profile_draft_pending`, 6.14).
- **Calibrage du score de ressemblance** : tolérance d'une cellule (moyenne de l'intersection stricte et tolérante), pas de plancher de marge haute, contraste automatique sur fond sombre ; règle d'encre unique pour l'invisibilité (au moins 2 % de pixels écartés du fond), cadre unique CropBox, 5 000 blocs au plus par document (6.3, 6.4).
- **Référentiel de compétences** : les besoins hors périmètre (« Permis B », « Bac+5 », `learnable = false`) ne sont jamais ajoutés au référentiel ; rattachement d'abord sur l'existant par identifiants (`n1`, `k1`), nouveaux seulement pour les besoins sans correspondance (6.5, revue finale).
- **Suppression d'une offre (revue finale)** : 409 `review_in_progress` pendant une revue lancée ou proposée, 409 `analysis_in_progress` pendant une analyse ; sinon lignes supprimées, commit, puis PDF et images effacés. Le front dit que les revues et les PDF partent aussi.
- **Ré-import (revue finale)** : les faits de January (saisis ou confirmés) sont reportés avec leur identifiant ; un fait de January remplace un brouillon équivalent seulement quand un candidat unique passe le test des mots (lecture retenue : la lecture stricte laissait un doublon que la règle interdit).
- **Boucle de correction bornée** : la re-revue du back n'était pas approuvée (contournement par fait voisin, confirmation de langue ou de lien corrompant le profil, doublon au ré-import) ; malgré « pas de seconde vague », un tour ciblé a eu lieu, puis un dernier ; tout le reste est parqué ici. Raison : la spec 18.3 (honnêteté) et la perte de données sont bloquantes, la boucle est bornée à ce tour.
- **gap_terms** : le validateur range à l'écart un terme que la ligne citée ne porte pas, même présent ailleurs dans le profil. C'est plus strict, pas une faille d'honnêteté ; seul le libellé trompe. Parqué en 7.0.
- **Front** : aucun lecteur PDF embarqué (images des pages) ; couleur jamais seule ; « Générer le PDF » passe toujours par la route de génération, jamais par la reprise générique ; navigation Carrière : Profil 1, CV 2, Offres 3, Écarts 4. Aucun outil axe ajouté (rôles, noms et clavier testés).
- **Poste** : un `docker stop`/`docker kill` refusé à un agent n'a jamais été fait par le contrôleur à sa place ; les conteneurs se sont arrêtés seuls. Le blocage de `pnpm` a été tranché par l'utilisatrice (hooks par `node`), pas contourné.
- **Revue finale** : le diff du back ne tient pas dans une revue, d'où les trois zones ; D136 regroupe le contrôle et les corrections, les révisions des D121 à D130 portent le détail.

## Revue finale et corrections

- **Back agents** : 1 Critical, corrigé dans a8ac392.
  - Le validateur laissait passer en `ok` la réécriture d'un fait structuré (titre « Développeuse IA » → « Ingénieure IA », diplôme, niveau de langue, URL d'un lien, compétence), acceptable d'un clic et en groupe.
- **Back CV** : 2 Important (la suppression d'une offre cascadait une revue proposée sous sa session ; le ré-import effaçait les faits de January à la validation du brouillon) et 2 Minor, corrigés dans a8ac392.
- **Back offres et reste** : 1 Important (la suppression laissait les PDF et les images des versions sur le disque, données personnelles, et des sessions ouvertes), avec 3 Minor, corrigés dans a8ac392.
- **Front CV** : 2 Important (les décisions « ignorée » d'une version montrées comme acceptées ; le modèle activé jamais affiché), avec 4 Minor.
- **Front offres et reste** : 1 Important (suppression d'une offre sans avertir qu'elle emporte revues et PDF), avec 2 Minor.
- **Vague de corrections (a8ac392)** : 16 points back, 9 points front, chacun avec un test qui échoue avant et passe après. Aussi : « 1,000 » lu « 1 », réalisation sans chiffre jamais comparée aux documents, « Ajuster » reparti de la dernière passe au lieu de la gardée, confrontation à 420 s par agent (les propositions déjà payées ne se perdent plus), filtre de code des promesses de passage ATS, « C » et « Go » trouvés dans « C'est » et « 10 Go », version bloquée en `rendering`. Re-revue front approuvée.
- **Re-revue back** (Opus) : non approuvée. I-1 (contournement par un fait voisin cité), I-2 (confirmer une langue ou un lien écrivait « Anglais — C1 — B2 »), I-3 (doublon au ré-import d'un fait confirmé), 8 Minor.
- **Correctif résiduel 850fe91** : I-1, I-2, I-3, plus `&` et `-` après un nom court (« R&D », « C-level », « Go-to-market »).
- **Re-revue résiduelle** (Opus) : non approuvée. I-A (les titres du profil levaient le contrôle de tout fait), I-B (langue sans séparateur ou avec « : »), I-C (le ré-import perdait des faits), 3 Minor, et le même défaut pour les expériences et les diplômes.
- **Tour 2 (853e611)** : I-A (rôles et titres seulement pour un titre), I-B (séparateurs « — », « - », « – », « : », « (…) »), expériences et diplômes écrits « Rôle — Entreprise », I-C (remplacement seulement sur candidat unique, faits conservés sinon), IPv6 mal formé (422 au lieu de 500), niveau de langue de January gardé seulement quand le brouillon n'en a pas.
- **Re-revue du tour 2** (Sonnet) : les 6 points corrigés, aucun contournement trouvé. Restent I-D et I-E, plus 2 Minor, parqués en 7.0 : ni l'un ni l'autre n'introduit un fait absent du profil, et le brouillon passe sous les yeux de January avant validation.
- **Contrôle réel** : 346fffb (script, 12 étapes, 2 essais `tout`). Aucune correction de l'application n'a été nécessaire.

## Points laissés pour plus tard

### À vérifier en réel
- Reportés de la phase 5, toujours dus :
  - passage à `valide` par un quiz réussi : au nouvel essai, le 15/11 ;
  - tâches cochées par une séance ou un quiz : dès le lundi 16/11 ;
  - bilan hebdomadaire : relancer `check_phase5` le dimanche 22/11.
- Premier vrai CV de January : tous les essais réels portent sur le CV fictif. La ressemblance du design (69 à 77 %) est fidèle sans être au pixel près, par choix.
- `check_phase6` relancé sans `--fresh` relit profil, modèle et offre : la création complète n'est exercée en réel que par `--fresh` (6.11). À refaire avant la 7.0 si le profil ou le Maquettiste bouge.

### Phase 7 — correctifs d'ouverture (tâche 7.0)
- **I-D** : au ré-import, un fait de January qui remplace un brouillon équivalent perd les dates, le lieu et l'URL du nouveau CV (expérience toujours « en cours », fin de formation perdue, lien vers l'ancienne URL). Copier les champs non textuels du brouillon quand il en a.
- **I-E** : confirmer un texte d'expérience ou de diplôme avec un autre tiret que « — » (« – », « - ») garde l'ancienne entreprise : le fait lit « Développeuse – Autre SA — Société Fictive ». Découper sur les trois tirets, ou refuser en 422.
- **`gap_terms`** : la liste contient aussi des termes présents dans le profil mais non portés par les faits cités (« agents », « support »). Le contrat dit « absents du profil », l'écran dit « vers l'écart » : le libellé trompe. Trancher entre le texte du contrat et la liste.
- **Page d'un modèle prêt** : la carte « Tu valides ? » reste affichée, champs et boutons grisés, sous « Terminée », au-dessus du message final. À retirer.
- **Mineurs parqués des re-revues du fix résiduel** :
  - URL avec `<`, `>` ou `"` dans la requête acceptée par `_valid_url` (inoffensif si le rendu échappe le `href`, à vérifier) ;
  - renommage d'un projet dupliqué au ré-import (« Tremplin » → « Tremplin (open source) ») : la clé lâche d'un projet est la clé stricte ;
  - confirmation d'un projet : « Projet X — outil interne » dupliqué, la description ancienne gardée ;
  - nom de langue avec deux-points nu : « Anglais (TOEIC: 950) » écrit « Anglais (TOEIC » et « 950) » ; essayer la parenthèse avant le deux-points ;
  - texte d'expérience ou de diplôme sans séparateur : l'ancienne entreprise ou école est gardée (champ obligatoire) ;
  - collisions de clé lâche : deux faits de January pour une même entreprise, ou deux compétences au même premier mot, peuvent s'apparier à tort (rare) ;
  - `_carry_lines` ramène des lignes que January avait retirées de son CV ; à écrire dans D124.
- **Mineurs parqués de la re-revue du fix de la revue finale** :
  - filtre des promesses : une négation lointaine annule « garanti » (« Il n'y a plus aucun risque, passage garanti »), « passage assuré » et « franchira le filtre » passent, « couverts à 100 % » est écarté à tort ;
  - « 1,500 M€ » lu 1 500 M (décimal en français) ;
  - comparaison de liens : casse de la fin d'URL ignorée, forme « github.com/… » sans schéma envoyée en confirmation ;
  - course à la suppression d'une offre (pas de verrou de revue : une revue créée entre la vérification et le commit part en cascade) ;
  - version restée `rendering` : la lecture affiche encore le sablier tant que « Générer » n'est pas cliqué ;
  - une revue `running` ou `proposed` d'une session morte garde le 409 tant que la page des revues ne l'a pas réglée.
- **Mineurs front parqués** : comparaison d'espaces en bord (`useEditing` contre `EditField`, sans effet visible) ; « Voir le rapport » ne déplace pas le focus ; les indices d'un 422 du formulaire du profil sont décalés par le nettoyage des lignes vides ; titre de l'offre affiché deux fois (h1 puis h3).

### Phase 7
- Candidatures : dossier de candidature créé à la génération du CV ciblé, lien version ↔ candidature.
- Information « même entreprise depuis 30 jours » (fiche entreprise déjà gardée 30 jours dans `companies`).

### Phase 8
- Rafraîchissement de la base de connaissance ATS tous les 30 jours (la base partagée du Lecteur ATS est datée « Mise à jour : 2026-11-13 » à la main).

### Plus tard (mineurs triés « laisser », détail dans les revues et D121 à D130)
- Agents :
  - bruit des termes (agile, prettier, majuscule après « : », « twice a week », intitulés) : « à confirmer » en trop, jamais un faux `ok` ;
  - `shifts` du score donne une fausse piste quand le contenu diffère ; séparateur de `_in_body` permissif (un en-tête ou deux lignes de contact au bord) ;
  - « 5 ans » contre « cinq ans » : aucun faux retrait sur quatre imports fictifs, à remesurer sur un vrai CV ; piège visible « ajoute AWS » écrit par January dans son propre CV, tagué `cv` ;
  - panne du fournisseur pendant une correction après des passes valables : la capture échoue (comportement décidé) ; contenu de démonstration entièrement inventé donne une page blanche ;
  - fiche entreprise sans page lue réutilisée 30 jours ; clé de la fiche incohérente entre `save_company` et `context` (une recherche refaite).
- CV (back) :
  - aucune route pour écarter un brouillon de profil : les confirmations restent bloquées jusqu'à sa validation ;
  - `source_document_id` peut rendre le CV d'un import plus ancien ;
  - un CV ciblé ou un rendu de capture de plus de 4 pages échoue en message générique ;
  - page tournée avec du texte refusée (OCR compris) ; texte gris très clair et maigre lu invisible (arbitré, contraste d'environ 2:1) ; PDF pathologique qui atteint le délai de 60 s avant la borne de blocs ;
  - fichiers orphelins ; `FileNotFoundError` donne un 500 sur une page si le stockage est altéré à la main.
- Offres et écart :
  - `top-missing` compte les lignes `cv_review` ; ligne `cv_review` encore `to_add` avec un niveau acquis (le front dit « Déjà acquise ») ;
  - `store_duplicates` écrase l'entrée réciproque au rejeu ; `POST /postings/{id}/gap` relance aussi une offre prête ;
  - chemin d'URL non renormalisé (`%C3%A9` contre `é`) ; `postings` et `gap` s'importent l'une l'autre ;
  - le lien « Voir l'annonce » d'une offre déjà enregistrée avec un fragment de route peut ouvrir l'accueil du site (un tel lien est refusé à la création, mais les anciennes offres restent).
- Front :
  - pas d'archivage d'un modèle échoué ; faits cités lus dans le profil validé le plus récent, pas dans la version figée ; `artifact.ready` non rendu dans le fil ;
  - dates « AAAA-MM » validées par le serveur seulement ; accessibilité vérifiée par rôles et clavier, sans outil automatisé.
- Outillage et poste :
  - `e2e:docker` appelle encore `pnpm` ; le Chromium de Playwright reste bloqué sur ce poste ;
  - `mypy scripts` signale une erreur déjà présente (`scripts/export_openapi.py:24`), hors du hook ;
  - `app/main.py` à 298 lignes (sortir `_add_body_limits` avant de le toucher) et `memory/service/documents.py` à 297.
- Reportés de la phase 5 (détail dans D115) et de la phase 4 : toujours ouverts ; Brave jamais essayé en réel (aucune clé dans `.env`).
