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
