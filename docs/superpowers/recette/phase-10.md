# Recette réelle de la phase 10 (10.S, version courte)

17/11/2026, `dev` à d72e329 (arbre exporté par `git archive`, images construites depuis cet export :
back et bac à sable). Pile jetable `learning_career_platform-check10-*` : volumes `app_data` (80 Mo),
`qdrant_data` et `ollama_data` **copiés** de la vraie pile (jamais montés tels quels), back sur le
port 8120, `SCHEDULER_ENABLED=false`, `AUTH_MODE=local`, front non lancé (tout passe par l'API HTTP).
Le `.env` n'a pas été lu : seules les trois lignes `ZAI_*` en ont été copiées dans l'arbre exporté
(Anthropic, OpenAI et Brave volontairement absents ; la santé le confirme : « Anthropic : aucune
clé »). Tous les niveaux de modèle de la copie sont sur `glm-5.3-flash`. La vraie pile n'a pas été
touchée. Aucun jeton ni clé ci-dessous (masque `tmcp_…`).

## Résultats

| N° | Point | Résultat |
|---|---|---|
| 1 | Migration 0016 sur la copie | ✅ journal : `0014 -> 0015`, `0015 -> 0016` ; `alembic current` = `0016 (head)` = `alembic heads` ; 0 erreur ; `/health` : 7 contrôles verts dont `sandbox`. |
| 2a | `initialize` | ✅ 200, `protocolVersion 2025-06-18`, `serverInfo tremplin 1.0.0`, `instructions` présentes (1 479 signes). |
| 2b | `tools/list` | ✅ 155 outils ; identique, nom pour nom, à `GET /mcp/actions` (voir tableau). |
| 2c | Niveau 1 | ✅ `costs_get_report` : 622 appels, 1,657504 $ (les chiffres de la copie) ; `costs_list_calls`, `ide_list_exercises` : `ok`. |
| 2d | Niveau 2 | ✅ `postings_write_posting` : offre `ready` (postings 1 → 2), **aucun** graphe lancé (sessions 68 → 68, aucune ligne de coût), 1 entrée dans `/mcp/changes` (3 lignes : offre, élément de mémoire, écriture). Annulation `POST /mcp/changes/{id}/undo` : 200, `undone: 3`, postings 2 → 1. |
| 2e | Niveau 3 | ✅ `postings_delete_posting` : `pending_confirmation` + `confirmation_id` ; l'offre est **encore là** (postings 2) ; la demande porte l'aperçu (`request` : méthode, route, `target_label` entouré de `<donnee_non_fiable>`, résumé) ; `POST /mcp/confirmations/{id}/confirm` (API de l'interface) : 200, `confirmed`, offre retirée (postings 1). |
| 2f | Niveau 4, inconnu, accès | ✅ `settings_set_tiers`, `keys_create`, `mcp_create_token`, `account_delete_all`, `nope_unknown` : JSON-RPC `-32602 Outil inconnu`. `settings_update_preferences` n'a ni `tiers` ni `agent_overrides` dans son schéma. Sans jeton 401 ; faux jeton 401 ; `Origin` étrangère 403 ; argument en trop : `invalid_arguments` ; jeton lecture seule sur un outil d'écriture : 403 `write_not_allowed` ; hors portée : 403 `feature_not_allowed` ; interrupteur général coupé : 403 `mcp_disabled`. |
| 2g | Jeton révoqué | ✅ `DELETE /mcp/tokens/{id}` 204, puis appel : **401 `mcp_token_revoked`**. Le jeton n'apparaît ni dans `/mcp/calls` (35 appels) ni dans les 134 lignes de journal du back (0 WARNING, 0 ERROR). |
| 3a | Séance par MCP | ✅ `ide_create_session` : séance, `passed = false`, `file_hashes` présents. |
| 3b | `ide_write_file` interrupteur éteint | ✅ refusé : `mcp_ide_write_off` (message « Propose plutôt une correction dans une note »). Via `/mcp` : HTTP 200 avec `isError: true` (les erreurs d'outil ne portent pas le code HTTP ; 403 côté route). |
| 3c | Interrupteur allumé par l'interface | ✅ `PUT /ide/preferences {mcp_can_write_files: true}` 200 ; l'écriture passe, l'interface lit le même contenu. |
| 3d | `base_hash` périmé | ✅ `stale_base` (route : 409), rien écrit. |
| 3e | Exécution par MCP | ✅ `ide_start_run` : `origin = mcp`, `ide_read_run` : `done`, sortie `2\n`, code 0, 76 ms ; identique par `GET /ide/runs/{id}`. |
| 3f | Vérification de Claude | ✅ exercice (2 fichiers) créé et ouvert par MCP, solution écrite par `ide_write_file`, `ide_start_run kind=check` : `1 passed`, code 0, `origin = mcp` ; la séance reste **`passed = false`**, `passed_at = null`. La même vérification lancée par l'interface (`origin = app`) : `passed = true`, `passed_at` posé. |
| 3g | Limite d'écritures | ✅ vu sans le chercher : 11e écriture dans la minute : 429 `rate_limited`, `retry_after: 4`, limite 10/minute (conforme aux docs). |
| 4 | Professeur réel | ✅ `POST /ide/sessions/{id}/teach` (`question`, fichier `main.py`) : 202, session d'agent `ide_teacher` `completed`, **1 appel**, `glm`/`glm-5.3-flash`, 995 jetons entrants, 321 sortants, **0,00093952 $** ; 1 note `explanation` de l'auteur `professor` (pas de bloc de code, relève que `sum(range(10))` n'est pas dans le fichier, pose une question) ; `/costs/calls` 622 → 623 appels, `/ide/usage?session_id=` : 1 316 jetons. |
| 5 | Bac à sable (`tests/sandbox_live`) | ✅ **26 passés**, 0 échec, 37 s, contre le conteneur de la pile jetable (utilisateur 10001, `--group-add 12345`, volume d'échange monté) : uid 20000 sans capacité, pas de réseau, pas de socket Docker, pas de secret dans l'environnement, système de fichiers en lecture seule, écriture seulement dans `/work` et `/tmp`, pas d'exécution depuis `/work`, spool et `/proc` du lanceur illisibles, lanceur non tuable, `mount`/`ptrace`/`unshare` refusés, seccomp actif, boucle CPU coupée, bombe mémoire tuée, bombe de processus contenue, disque et inodes bornés, mémoire partagée vidée, sortie tronquée, travail forgé ignoré, restes nettoyés, bac utilisable après les abus. Après les tests : bac `healthy`, 0 redémarrage (le drapeau `OOMKilled` du conteneur reste vrai : trace de la bombe mémoire tuée dans son groupe de contrôle). Rejeu par la route réelle (`POST /ide/.../runs`) : connexion vers `1.1.1.1`, `qdrant`, `backend` refusées, écriture dans `/etc` refusée, 0 variable de clé, `/spool` : `PermissionError`. |
| 6 | Docs de configuration | ✅ voir plus bas : aucune correction nécessaire. |

## Tableau des niveaux (155 outils exposés, `tools/list` = `/mcp/actions`)

| Niveau | Outils | Détail |
|---|---|---|
| 1, lecture | 74 | routes |
| 2, écriture annulable | 65 | 60 routes + 5 parcours `graph_*` (`web_research`, `program_builder`, `lesson_factory`, `learning_council`, `learned_document`) |
| 3, demande « À confirmer » | 16 | `cv_archive_template`, `cv_decide_modification`, `cv_generate_version`, `cv_put_profile`, `ide_delete_exercise`, `learning_choose_proposal`, `memory_add_text_document`, `memory_create_item`, `memory_delete_item`, `memory_merge_items`, `memory_reindex_memory`, `memory_update_item`, `postings_delete_posting`, `program_validate_program`, `projects_add_profile_entry`, `sessions_answer_session` |
| 4, jamais exposé | 0 | aucun outil de clés, de compte, de modèles ni de jeton ; 23 features à la création du jeton |

## Constats

- **Mineur M1.** `postings_write_posting` : le schéma d'outil n'annonce pas le minimum du champ `text`
  (300 signes et 50 mots, vérifié par le modèle Pydantic). Un texte court répond « Arguments
  invalides : text » sans dire pourquoi ; Claude doit deviner. Proposition : écrire le minimum dans
  la description de l'outil ou dans le message d'erreur.
- **Note N1.** Les refus d'outil (`mcp_ide_write_off`, `stale_base`) arrivent en HTTP 200 avec
  `isError: true` ; les refus d'accès (jeton, portée, lecture seule, interrupteur, limite) arrivent
  en 401/403/429. Cohérent avec le protocole, mais un client qui ne lirait que le code HTTP ne verrait
  pas les premiers.

## Docs (point 6) : `docs/mcp/AGENTS.md` contre les docs officielles (17/11/2026)

- Claude Code (`code.claude.com/docs/en/mcp`) : `claude mcp add --transport http <nom> <url>
  --header "Authorization: Bearer …"` : la ligne du guide est exactement la forme documentée
  (`-t`, `-H` existent en court). La page ne dit pas si un serveur sans GET (POST seul) est accepté ;
  `GET /mcp` répond ici 405 `Allow: POST`, forme prévue par la spécification MCP pour un serveur sans
  flux. Non rejoué avec le vrai client (pas de modification de la configuration de l'utilisatrice).
- Codex (`developers.openai.com/codex/mcp`, redirigé vers `learn.chatgpt.com/docs/extend/mcp`) :
  `[mcp_servers.<nom>]`, `url`, `bearer_token_env_var` (nom d'une variable d'environnement), sans
  drapeau expérimental : conforme au guide.
- **Corrections nécessaires : aucune.**

## Limites

Front non lancé (aucun écran regardé) ; pas de vrai client Claude Code ni Codex branché ; écran
« Accès MCP » et page IDE non vus ; un seul appel professeur ; copie à chaud des volumes.
Dépense : GLM 0,00093952 $ (1 appel, `glm-5.3-flash`), Anthropic 0.
