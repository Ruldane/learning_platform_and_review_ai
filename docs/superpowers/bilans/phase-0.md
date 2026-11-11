# Bilan de la phase 0 (socle)

Tag `phase-0` (9ef12a4). Revue complète Opus + vague de corrections (10 constats) approuvée.

## Arbitrages pris pendant l'exécution

- | 0.1 | git init, .gitignore | déjà faits par le contrôleur (main + dev, .gitattributes LF) | Ruling: 0.1 saute git init, complète .gitignore existant — déjà fait — rien perdu |
- | 0.1 / 0.2 / 0.14 | .pre-commit-config | 0.1 demande mypy + lint-imports avant que app/ et les contrats existent | Ruling: 0.1 installe ruff + check_file_length ; mypy ajouté en 0.2 ; lint-imports en 0.14 — sinon hooks en échec — coût faible |
- | 0.1 | Python | Python 3.14 local, Docker 3.12-slim | Ruling: .python-version = 3.12 via uv pour parité local/Docker |
- | 0.2 / 0.3 / 0.4 | fixture app + lifespan | httpx ASGITransport ne lance pas le lifespan ; 0.4 dépend du lifespan (ensure_local_user) | Ruling: fixture `client` utilise asgi-lifespan LifespanManager ; DB de test = fichier tmp_path + create_all avant démarrage (lifespan ne crée pas de tables, entrypoint lance alembic) |
- | 0.10 / 0.14 | Docker | Docker Desktop non démarré | Ruling: le contrôleur lance Docker Desktop avant 0.10 |
- Ruling: remote origin = https://github.com/Ruldane/learning_platform_and_review_ai (fourni par l'utilisatrice) ; push de dev à chaque fin de tâche validée et à chaque fin de phase — c'est l'usage voulu du dépôt — coût si faux : historique distant à nettoyer.
- Task 0.2: complete (commits 090ba1f..fd661bf, review clean) — Ruling: mineurs 1 (headers HTTPException), 2 (message http_error en français), 6 (fixture settings isolée de .env) intégrés à 0.3 ; mineurs 3,4,5 (tests http_error, asserts mypy, CORS sur 500) reportés à la revue finale
- Task 0.4: complete (commits 4938c8e..154cb3d, review clean) — Ruling: mineurs 1 (OperationalError trop large) et 2 (test redémarrage 2 lifespans) portés en 0.5 ; mineurs 3-6 (user_not_found non testé, settings via app.state, MeOut.auth_mode Literal, email None en local, unicité user local) différés
- Task 0.7: Ruling: mineur 1 (GlmProvider de LLM_PROVIDERS ignore zai_base_url pour test_key/list_models) porté en 0.8 (bootstrap construit GlmProvider(base_url=settings.zai_base_url)) — load-bearing pour le test de clé GLM
- Task 0.9: Ruling: mineurs 2 (contrôle JSON SearXNG sous 3 s, 403 limiter) et 4 (client httpx créé hors try dans le lifespan) portés en 0.10 — conditionnent /health au vert sous Docker
- Ruling: ports hôtes rendus réglables (${FRONTEND_PORT:-5173}, ${BACKEND_PORT:-8000}, ${QDRANT_PORT:-6333}) avec CORS_ORIGIN cohérent — porté en 0.14 — défauts de la spec conservés
- Task 0.10: Ruling: commentaires de .env.example déplacés sur leur propre ligne (contenu de SPEC 16.2 conservé, mise en forme seule déviée, D31) + test qui interdit tout commentaire en ligne dans .env.example — la spec veut un premier lancement fonctionnel, sa mise en forme le casse — coût si faux : nul (purement cosmétique)
- Task 0.13: Ruling: mineurs 2 (clé gardée dans mutation.state.variables après échec) et 3 (reset() d'un save détache l'observateur d'un autre save en cours) promus dans la boucle — même code, durée de vie de la clé = règle de sécurité contraignante — coût si faux : quelques lignes
- Ruling: vague finale = 5 Important + mineurs 1 (commande export_openapi dans le plan phase 1), 3 (ModelChoice min_length=1), 5 (CORS localhost + 127.0.0.1, CORS_ORIGIN documenté), 6 (tableau du plan directeur : HEALTH_CHECKS dans bootstrap) + constat GLM (test_key/list_models via GET /models, 429 lisibles) — tous petits et load-bearing pour la phase 1 ou pour l'utilisatrice — coût si faux : quelques fichiers
- Ruling: mineur 2 (retries SDK x invoke) tranché en tâche 1.5 : max_retries=0 dans build, invoke possède les retries — à porter dans le brief 1.5
- Ruling: mineur 4 (fr.ts découpé par zone + agrégateur) avant la phase 2 — à porter dans le plan phase 2
- Ruling: notes phase 1 (Origin vérifié sur WebSocket ; politique shared/session-ui pour components/ en 1.11 ; app.agents ajouté aux contrats 3 et 4 ; GLM reasoning_content : désactiver thinking ou max_tokens suffisant) — à porter dans les briefs phase 1
- Ruling: liste des modèles GLM = ids de /models ∪ modèles des préréglages du fournisseur (glm-4.7-flash absent de /models mais fonctionnel) — porté en phase 1 (tâche qui touche providers/llm) — coût si faux : un modèle de préréglage non resélectionnable dans la liste

## Points mineurs laissés pour plus tard

- Task 0.3: minor (deferred): test rollback faible ; dispose non testé ; list sans ORDER BY ; updated_at écrasable ; UserSettingsRow.data sans MutableDict (0.6 doit réassigner le dict) ; pas de test downgrade
- Task 0.3: minor (deferred): DECISIONS D22 items (8)/(7) dans le désordre ; alembic/ hors mypy
- Task 0.5: minor (deferred): secret.key vide après crash (écriture atomique) ; variantes encodées non masquées ; handlers ajoutés après coup / extra= non couverts ; KnownSecrets sans reset() ; test mal nommé (mapping) ; test env keys global faible
- Task 0.5: minor (deferred): secret coupé entre gabarit et argument non détecté
- Task 0.6: minor (deferred): complétion des tiers non testée ; tier inconnu en base remet tous les tiers à Haiku ; pas de contrôle min<=max week-end ni délais >0 ; course premier PUT non notée ; replace pourrait persister vision_enabled si SettingsOut passé
- Task 0.7: minor (deferred): pagination Anthropic sans plafond ; constantes timeout/retries dupliquées ; fixture _Keys obscure
- Task 0.7: minor (deferred): raise from exc garde la cause UnicodeEncodeError ; plafond 50 pages tronque silencieusement
- Task 0.8: minor (deferred): models_overview séquentiel (gather) ; get_cipher/get_llm_factory inutilisés (deux sources de cipher) ; assert en prod keys_repository ; test_key_never_logged faible ; test_bootstrap appelle _url privé ; has_key=False ambigu pour clé illisible
- Task 0.8: minor (deferred): _usable_key lu deux fois par fournisseur ; msg des 422 pourrait un jour contenir la valeur (règle ajoutée aux contraintes)
- Task 0.9: minor (deferred): pas de log serveur des contrôles en échec ; client non fermé + _NO_USER dans test_bootstrap ; test de parallélisme temporel ; DB_CHECK dupliqué, import httpx dans le service
- Task 0.10: minor (deferred): timeout implicite hors Protocol HealthCheck (_cap/getattr) ; /health attend jusqu'à 15 s tant que SearXNG JSON échoue ; ollama/ollama-init démarrent même avec OLLAMA_BASE_URL hôte (README : ollama pull bge-m3 sur l'hôte) ; ports 8000/6333 sur toutes interfaces (127.0.0.1 en 0.14) ; Compose >= 2.24 non documenté ; entrypoint dev sur 150 caractères ; nginx sans gzip ni server_tokens off
- Task 0.11: minor (deferred): anneau de focus du bouton shadcn à 50 % (~2:1, < 3:1 AA) écrase l'outline global ; pas de contrôle schema.d.ts périmé vs openapi.json ; <main id="contenu"> sans tabindex=-1 pour le lien d'évitement ; pas d'étape rouge back ; classes inutilisées dans button.tsx
- Task 0.11: minor (deferred): instanceof Error peut rater un DOMException d'un autre realm
- Task 0.12: minor (deferred): NAV_GROUPS calculé au niveau module depuis FEATURES alors que buildRoutes prend la liste (couplage caché) ; refetchInterval 30 s et signal non testés ; <h2> de section dans la nav ; key=path sans garde de doublon ; sidebar fixe w-56 sans comportement mobile
- Task 0.13: minor (deferred): erreur de refetch en arrière-plan remplace toute la page (isError && !data) ; saisie libre sans affichage optimiste, perdue si PUT échoue ; choix fournisseur en attente survit à un préréglage ; préréglage/tier manquant -> choix vide envoyable ; clé i18n settings.models.loading inutilisée ; useActionError/useTierActions sans tests propres ; Supprimer sans confirmation ; contrastes emerald/amber non vérifiés ; tableau 3 colonnes en largeur mobile
- Task 0.13: minor (deferred): pas de test "A échoue pendant que B est en vol" ; effacement du champ écrase une saisie faite pendant la requête ; hasText dépend d'onChange (autofill) ; delete/test n'affichent occupé que le dernier fournisseur
- Task 0.14: minor (deferred): voyant vert avec une clé dont le test a échoué (check llm = clé lisible seulement) ; GET /settings/models appelle chaque fournisseur à chaque ouverture (401 en WARNING) ; hook lint-imports commité un commit avant les contrats ; app.db en 644 (secret en 600)
- Task 0.14: minor (deferred): motifs ignore import-linter ne couvrent pas un service devenu paquet ; contrat 3 énumère les fournisseurs concrets ; test_compose substring faible ; CORS_ORIGIN non documenté dans .env.example ; détail santé tronqué à droite dans la barre du haut ; callback Google à dériver de BACKEND_PORT (phase auth)
