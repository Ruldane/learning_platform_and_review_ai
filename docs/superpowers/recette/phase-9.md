# Recette réelle de la phase 9 (9.S + 9.Q)

17/11/2026, branche `dev` (HEAD 9078433), image construite depuis ce HEAD. Pile jetable
`learning_career_platform-check9-*` : copie des volumes `app_data` (80 Mo) et `qdrant_data`
(763 Mo) de l'utilisatrice (copie à chaud, sans arrêt de la vraie pile), ports 8110 (back) et 5190
(front), Ollama jeté sur un volume vide. Les vrais conteneurs et volumes n'ont jamais été montés en
écriture ; `.env` n'a jamais été lu. Aucune donnée personnelle ci-dessous : nombres, codes, durées.
Durée : 21 min de pile, environ 35 min en tout (plafond 1 h). Dépense : GLM 0,0029 $ (2 appels) ;
**Anthropic 0,0188 $ (25 appels), non voulue, voir I1**.

| N° | Point | Résultat |
|---|---|---|
| 1 | Porte du premier lancement sur la copie | ✅ `onboarding_done = true`, l'ouverture de `/` reste sur « Ton brief du jour », jamais `/bienvenue`. |
| 2 | Coûts : écran = `GET /costs/calls` | ✅ Avant la capture : 622 appels, 1,657504 $ (somme des 622 lignes de `/costs/calls`). Après : 623 appels, 1,658955 $ (somme des lignes : 1,65895475 ; le rapport arrondit à 6 décimales), 2 436 649 jetons entrants et 349 476 sortants des deux côtés. L'écran affiche 623 appels, « 1,66 $ », et la ligne du jour : 3 appels, « 0,003 $ » (somme des 3 lignes du jour : 0,0025717). Capture : 1 appel, 2 592 jetons entrants, 158 sortants, 0,0014505 $. |
| 3 | Modèle par agent (`capture`, agent `archivist`) | ✅ avec réserve. La surcharge est lue et appliquée : `archivist` surchargé sur `glm-4.5-air`, `glm-5.3-flashx`, `glm-5-turbo`, `glm-5.3` donne à chaque fois une session en échec `llm_credit_exhausted` (« Crédit Z.ai insuffisant pour ce modèle », 0 jeton, aucune ligne de coût) : le forfait Z.ai de l'utilisatrice ne couvre que `glm-5.3-flash`. Preuve de la priorité de la surcharge sur le niveau : niveau `rapide` mis sur `glm-4.5-air` (en échec) et surcharge `archivist` sur `glm-5.3-flash` : la capture réussit, `/costs/calls?graph=capture` montre `glm-5.3-flash`, 2 595 jetons entrants, 131 sortants, 0,0014122 $. Réglages remis à l'identique (comparaison octet à octet avec la copie d'origine). Non joué : une surcharge vers un modèle **différent et réussi** (Anthropic) : l'action a été refusée par le contrôle de l'environnement (seul GLM était autorisé), je n'ai pas contourné. |
| 4 | Export sans clé ni secret | ✅ `GET /account/export` : 200, 7 816 241 octets, 3,1 s, `tremplin-export-AAAAMMJJ.zip`, `no-store`, 84 fichiers (52 tables JSON, 31 fichiers déposés, manifeste). Occurrences comptées : `api_key` 25 (textes de pages en cache, leçons et événements de session, et la ligne `"api_keys": 0` du manifeste, seule clé JSON), `sk-` 17 lignes dont **0** de forme clé (`sk-` suivi de 20 caractères ou plus : ce sont des exemples dans des textes appris), `sk-ant` 0, forme clé GLM 0, `APP_SECRET` 0, `encrypted` 0, blob chiffré (`gAAAA…`) 0. La copie n'a aucune clé en base (clés du `.env`, `api_keys.json` vide). Épreuve ajoutée : une fausse clé OpenAI de 33 caractères enregistrée, nouvel export : 0 occurrence de la clé, de son préfixe ou de son milieu ; la ligne exportée porte `provider`, `last4`, dates, sans `encrypted_key`. Fausse clé retirée (204). |
| 5 | Embedding : vrai `pull` de `bge-m3` | ✅ Volume Ollama vide. À l'ouverture du back : `present = false`, `percent = null` (« Téléchargement de bge-m3 en cours. »), puis 5, 9, 11, 17, 24, 28, 32, 36, 41, 46, 52, 58, 62, 69, 76, 82, 86, 91, 96, 99 puis 100 % (lecture toutes les 5 s, croissante, 112 s de 5 % à `present = true`, « Le modèle bge-m3 est prêt. »). `/health` : `ollama` rouge pendant le téléchargement (`status = degraded`), puis `ok`. |
| 6 | Mode Google, faux fournisseur | ✅ Back en `AUTH_MODE=google` (faux OIDC `backend/scripts/fake_oidc.py` dans l'espace réseau du back : le point `token` doit être en boucle locale), `ALLOWED_EMAILS` = deux adresses nommées. Sans session : `/auth/me` 401, `/health` 200. Adresse non nommée : `/connexion?erreur=email_not_allowed`. Première adresse nommée : redirigée vers `/connexion/reprise`. Seconde adresse nommée, avant tout choix : aussi `/connexion/reprise` ; la première reprend (`take_local` : 200, **même `id`** que l'espace local, 624 appels et 1,660367 $ intacts), la seconde `take_local` : **409 `local_already_claimed`**, puis `fresh` : 200, nouvel `id`. Isolation : 17 routes lues avec les deux cookies (coûts, journal, objectifs, documents, mémoire, profil, programmes, projets, ressources, sessions, offres, candidatures, carte, rappels, relevés, brief, réglages) : le second compte ne voit **rien** du premier : 14 listes vides de son côté (2 à 36 octets) contre 218 à 99 037 octets chez le premier (les rappels sont vides des deux côtés) ; les seules réponses plus longues du second (statistiques de la mémoire à zéro, profil vide, son propre brief, ses réglages par défaut) sont les siennes. Coûts du second : 1 appel (le sien). WebSocket `/sessions/{id}/stream` depuis un client hors navigateur : sans cookie sans `Origin` 401 ; sans cookie avec `Origin` 401 ; cookie **sans** `Origin` 403 (refusé) ; cookie + `Origin` du front **accepté** (premier message reçu) ; cookie + `Origin` étrangère 403 ; cookie du second compte sur la session du premier : accepté puis fermé en **4404**. L'écran de reprise lui-même : parcours n° 5 (Edge, 2d53752), non rejoué ici. |
| 7 | « Tout supprimer » | ✅ Mode Google, premier compte : confirmation fausse 422 ; `SUPPRIMER` **204**, `Set-Cookie … Max-Age=0`, `/auth/me` 401 ; points Qdrant 213 → 0 ; fichiers déposés 1 dossier (3 048 Ko) → 0 ; le second compte intact (200, ses données) ; nouvelle connexion de la même adresse : nouvel `id`, espace vide (0 appel, listes vides). **Mode local** (rejeu sur une seconde copie, planificateur coupé pour ne rien dépenser) : confirmation en minuscules 422 ; **204** en 2,1 s ; points 209 → 0, fichiers 31 → 0, journal, mémoire, objectifs, coûts vides ; `/auth/me` 200 avec le **même** `id` ; `PUT /settings` 200 et export 200 ensuite (espace utilisable). Réglages remis aux défauts : niveaux Anthropic Haiku, `onboarding_done = false` (voir M2). |
| 8 | Journaux relus après coup | ✅ avec réserve. Relus : le conteneur du mode Google (196 lignes), celui du mode local qui l'a suivi (149) et celui du rejeu (0 WARNING, 0 ERROR, 0 e-mail, 0 lien). **Perdus** : les journaux du premier conteneur (local, téléchargement, captures), supprimés par la recréation du conteneur au passage en mode Google ; je ne les avais pas sauvés. Sur les 345 lignes relues : e-mails 0, noms des comptes d'essai 0, liens hors boucle locale 0, texte de note 0, motifs de clé ou de jeton (`sk-`, forme GLM, `Bearer`, secret du faux fournisseur, cookie de session, `code=`, `state=`) 0. WARNING 9, tous `search_unavailable` (requêtes `site:` connues, D164) ; ERROR 0 (les deux `sqlalchemy.pool` de D174 n'apparaissent plus). Les 4 sessions en échec `llm_credit_exhausted` du point 3 sont vues par leur code sur la session ; le seul WARNING lu avant la perte (`Appel LLM en échec : agent archivist, fournisseur glm, OpenAIRateLimitError (llm_credit_exhausted)`) ne porte ni clé ni texte. |
| 9 | Passage rapide des écrans (9.Q) | ✅ Edge (Playwright), 1 024 px, navigation **au clavier** (focus sur le lien du menu, Entrée). Neuf écrans : accueil (brief du jour), Étudier > Journal, Étudier > Quiz, Portfolio, Radar, Coûts, Réglages > Modèles et clés, Style, Mes données. Pour chacun : `scrollWidth = clientWidth` (1 009 = 1 024 moins la barre de défilement : **pas de défilement horizontal**), 0 `role="alert"`, 0 message de console (erreur ou avertissement) sur toute la session, `lang = fr`, focus sur le lien cliqué après chaque navigation (**jamais `body`**), aucun mot d'interface anglais (seul « Search » trouvé : « Brave Search », nom propre). |

## Constats

**Critique** : aucun.

**Important**
- **I1. Un compte neuf dépense avant d'avoir fini le premier lancement.** Au démarrage du back
  (planificateur), chaque compte sans réglage reçoit un brief du matin et sa recherche web, avec les
  niveaux par défaut (Anthropic Haiku 5.5) sur la clé du `.env`. Vu : 3 comptes neufs (deux comptes
  Google dont un à `onboarding_done = false`, un espace local neuf) : 25 appels, 78 941 jetons
  entrants, 21 768 sortants, **0,0188 $** chez Anthropic, en moins de 40 s, sans clic. Pour
  l'utilisatrice réelle (réglages sur GLM) rien ne change, mais en mode Google un invité nommé
  consomme la clé du serveur avant d'avoir choisi un modèle, et après « Tout supprimer » en mode
  local une relance du back refait la même chose sur Anthropic (réglages remis aux défauts). À
  arbitrer : ne rien planifier tant que `onboarding_done` est faux (ou que le compte n'a pas choisi
  de modèle). Cette dépense, hors de mon autorisation (GLM seul), est de mon fait : j'ai recréé le
  back sans couper le planificateur ; je l'ai arrêté dès que je l'ai vue, et le rejeu en mode local
  a tourné avec `SCHEDULER_ENABLED=false`.

**Mineur**
- **M1.** `POST /capture` avec un corps JSON en octets non UTF-8 (mon premier essai, texte accentué
  envoyé par le terminal Windows) répond une erreur `http_error` générique (« La requête n'a pas pu
  aboutir. ») sans nommer le champ ; non creusé (code de statut non relevé).
- **M2.** « Tout supprimer » en mode local remet les niveaux sur Anthropic Haiku (défaut) : une
  personne dont la seule clé est GLM doit refaire le choix à l'accueil (l'étape 3 de `/bienvenue`
  s'en charge, D195 n° 1) ; non vérifié dans le navigateur.
- **M3.** Les réglages proposent des modèles GLM que le forfait de l'utilisatrice ne couvre pas
  (`glm-4.5-air`, `glm-5.3-flashx`, `glm-5-turbo`, `glm-5.3`) : le message d'échec est clair mais
  n'arrive qu'à l'usage ; un test de modèle, en plus du test de clé, serait mieux placé.
- **M4.** Le téléchargement de `bge-m3` annonce `percent = null` pendant les premières secondes :
  l'écran qui le lit doit le montrer « en cours » sans pourcentage (non regardé dans le navigateur).

## Limites

Copie à chaud (le back réel tournait) ; WebSocket testé hors navigateur seulement ; reprise en
Google non rejouée dans l'interface (parcours n° 5) ; un seul navigateur (Edge) et une seule
largeur ; journaux du premier conteneur perdus ; surcharge vers un modèle d'un autre fournisseur
non jouée ; le rejeu de « Tout supprimer » en mode local s'est fait planificateur coupé.
