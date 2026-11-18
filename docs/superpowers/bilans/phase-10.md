# Bilan de la phase 10 (IDE Python avec professeur, serveur MCP)

Tag `phase-10`. Plan : `docs/superpowers/plans/2026-11-17-11-phase-10-ide-mcp.md`. 37 commits depuis
`phase-9`. Décisions D200 à D211 dans `DECISIONS.md` (D212 et D213 restent libres).

- **Organisation** : socle 10.P sur `dev`, puis quatre flux en parallèle dans quatre worktrees (A : IDE
  back et bac à sable ; B : adaptateur MCP ; C : IDE front et page Accès MCP ; D : déclarations MCP
  et garde de couverture), un seul écrivain par arbre ; intégration 10.I en deux temps. Deux tâches
  ajoutées en cours de phase à la demande de l'utilisatrice, chacune dans son worktree : **10.W**
  (écriture directe par MCP, sans agent) et **10.X** (Claude dans l'IDE en direct). Mode économie :
  Sonnet écrit et relit.
- **Tests** : back complet 6 373 passés à d72e329 (2 échecs, noms d'agents du fil d'activité,
  corrigés en 7667c47, `tests/features/activity` 30/30 ensuite) ; front 2 838 (480 fichiers) ;
  ruff, mypy strict, import-linter (9 contrats), longueur des fichiers, contrat OpenAPI verts.
- **Essai réel** (`docs/superpowers/recette/phase-10.md`) : pile jetable copiée des données,
  planificateur coupé, 6 points sur 6 ✅, 1 mineur. Dépense : GLM `glm-5.3-flash` 0,00094 $ ;
  Anthropic 0 $.
- **Quota hebdo** : 7 % au début de la phase, 27 % avant la clôture (plafond voulu : 25 %, dépassé
  par l'ajout de 10.W et 10.X).

## Ce que la phase apporte

- **IDE Python** (Monaco local) : exercices, séances, exécution et vérification par pytest dans un
  **bac à sable** sans réseau (runner séparé, uid 20000, tmpfs bornés, spool partagé, `sandbox_live`
  26/26 évasions refusées).
- **Professeur** en temps réel, styles guide ou binôme, indices par niveau, plafonds de coût ;
  exercices générés.
- **Serveur MCP** (`POST /mcp`, JSON-RPC) : 155 outils déclarés dans les manifestes des features
  (74 niveau 1 lecture, 65 niveau 2 écriture annulable, 16 niveau 3 « À confirmer », niveau 4
  jamais exposé) ; jetons `tmcp_` révocables, portées, interrupteur général, journal, annulation,
  carte « À confirmer » avec aperçu complet de la requête ; plafond de 30 lancements d'agents par
  jour compté à la source ; garde de couverture : toute route est déclarée ou exclue avec motif.
- **Écriture directe** (10.W, D210) : leçons, semaines et modules, projets, offres, quiz et
  questions, exercices d'IDE, sans agent ni LLM ; indexation mémoire différée et rattrapée par
  `mcp_housekeeping` ; quiz « en préparation » sous 8 questions et 3 types.
- **Claude dans l'IDE** (10.X, D211) : direct à 3 s onglet visible, origine des exécutions et notes,
  écriture des fichiers sous interrupteur (éteint par défaut, réglable seulement dans l'interface),
  `files_version` atomique, `base_hash`, aucune perte silencieuse dans un sens ou l'autre ; une
  vérification lancée par Claude ne valide jamais un exercice.
- **Guides** : `docs/mcp/AGENTS.md` et `CLAUDE.md` (pour Claude Code et Codex branchés sur Tremplin,
  règles courtes aussi servies à `initialize`), `AGENTS.md` et `CLAUDE.md` à la racine pour les
  agents de développement, lien dans le README.

## Arbitrages pris pendant l'exécution

- Contrat du socle complété avant les flux (déclencheurs du professeur, `check` = pytest, état
  `passed_at`, grammaire `untrusted`, `body_fields`/`merge_from`, journal des refus).
- `ide_teacher` et `ide_exercise` exclus du MCP : Claude enseigne par les notes, sans coûter l'API
  de l'utilisatrice.
- Plafond des lancements compté à la source (`LaunchQuota`, mémoire, remis à zéro au redémarrage
  comme les limites par minute) au lieu d'un comptage par déclaration (contournable).
- Écriture directe gardée au niveau 2 malgré l'entrée en mémoire : choix de l'utilisatrice
  (exception à D208 n° 2, écrite dans D210).
- Fin de phase réduite pour le quota : pas de parcours e2e dédié (tests unitaires et MSW + essai
  réel) ; revue finale Opus reportée à la **revue globale du projet après le reset hebdo** ; les
  correctifs des relectures de 10.W, 10.X et du recollage n'ont pas eu de revérification.

## Points laissés pour plus tard

- **Revue globale Opus** après le reset : couvrir en priorité les correctifs non revérifiés (10.W
  `00775ea`, 10.X `cc9f166`, recollage `c9a769c`) et l'adaptateur MCP.
- **Limite du mode local** (D204 n° 10) : un agent avec un terminal peut appeler lui-même
  `/mcp/confirmations/{id}/confirm` ; protection actuelle : les permissions du client. Piste : code
  PIN ou mode Google (10b).
- Mineurs MCP : schéma de `postings_write_posting` sans minimum du texte (refus sans raison) ;
  jeton et interrupteur vérifiés avant le `precheck` rejoué (jusqu'à 60 s), pas après ; annulation
  d'une suppression sans retour des enfants supprimés en cascade ; erreurs des routes non
  encadrées (M10) ; annulation d'un rendu de projet au-delà de dix captures ; `install_gate` sans
  features ; `users_with_unindexed` seule lecture sans `user_id`.
- Écriture directe non couverte : PDF et ressources d'une leçon, fiches de révision, suppressions,
  captures ; projet créé hors calendrier, semaine sans tâche.
- Fil d'activité : un exercice d'IDE réussi réutilise le genre `project`.
- Non vérifié en réel : l'interface à l'écran (Chromium de Playwright bloqué par Smart App
  Control) et un vrai client Claude Code ou Codex branché (JSON-RPC rejoué à la main).

## Revue finale (après le tag, 17–18/11)

Revue Opus plafonnée sur deux zones : le cœur MCP (dispatcher, jetons, niveaux, annulation,
confirmations, plafond) et les trois correctifs non revérifiés. Le cœur tient. Verdict : à
corriger, 0 Critical, 2 Important, corrigés en f176ff9 et 9233d97 (D212) :

- **I1** : Claude pouvait passer un quiz à la place de January, réviser ses fiches, rendre son
  projet, ou réécrire les tests d'un exercice. Ces actions deviennent des gestes de January :
  refus 403 `mcp_gesture_forbidden` sous identité MCP, et `mcp_ide_test_file` pour les tests.
- **I2** : l'écriture directe d'une offre tenait le verrou SQLite pendant Ollama/Qdrant. La
  recherche de doublons se fait désormais avant toute écriture.
- Mineurs pris : l'annulation fait avancer `files_version` ; `response_fields` est exigé sous
  `/settings` pour toute méthode ; les descriptions d'outils sont corrigées.

La revérification ciblée ne trouve aucun nouveau Critical ni Important. Restent parqués :

- **N1** : une séance libre dont le titre est une compétence peut recevoir des tests écrits par
  Claude, avec un plafond `en_cours`.
- **N2** : un `pytest.py` écrit par Claude, interrupteur allumé, masque pytest dans le bac. À
  fermer côté bac, en lançant pytest hors du dossier de travail.
- **N3** : la retouche d'une offre lit puis attend le réseau, ce qui peut écraser un « distinct »
  posé entre-temps.
- Les points parqués de D212 n° 6.
- La limite du mode local, **bloquante avant tout hébergement ou le mode Google**.

Incident de clôture : retirer le worktree `b` a vidé les paquets de `frontend/node_modules` (git a
suivi des liens). Ils ont été réinstallés par `npx pnpm@12.18.0 install --frozen-lockfile --force`,
avec l'accord de l'utilisatrice. Pour les prochains worktrees : supprimer tout lien vers l'arbre
principal avant `git worktree remove`, ou ne jamais en créer.
