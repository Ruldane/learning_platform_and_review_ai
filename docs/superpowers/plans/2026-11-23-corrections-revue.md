# Corrections de la revue de Tremplin

> **Pour les agents :** utiliser superpowers:subagent-driven-development. Écrire un test qui échoue avant chaque correction. Travailler sur le worktree de codex/reorganisation, à partir de 802f367.

**Objectif** — Corriger les huit constats de la revue, conserver les données des comptes et publier le lot vérifié.

## Effacement du compte

- [x] Associer le formulaire et la requête d’effacement à l’identité affichée. Refuser côté serveur une requête visant une autre identité. Conserver l’exécution MCP au niveau 3 et vérifier les deux comptes avec des sessions factices.
- [x] Assurer la reprise durable d’une purge vectorielle interrompue. Vérifier une panne après la transaction SQLite, la reprise au démarrage ou au passage de la tâche planifiée, et l’isolation d’un compte recréé.
- [x] Vérifier le parcours Playwright du compte et la migration sur une base de recette.

## Validation et CV

- [x] Protéger les deux formats de réponse 422. Garder les champs connus et indices nécessaires aux formulaires et utiliser des messages fixes en français. Vérifier les chemins créés depuis des clés dynamiques et la compatibilité des erreurs de champs légitimes.
- [x] Garder l’association de chaque chiffre avec sa mesure dans le CV ciblé. Vérifier qu’une permutation est soumise à confirmation et que la réécriture fidèle reste utilisable.

## MCP et conversations

- [x] Restreindre le journal MCP aux identifiants vérifiés, en conservant les identifiants produits par un appel réussi. Vérifier les appels en échec et leurs notices.
- [x] Passer la fin et l’abandon de la séance guidée au niveau 3. Vérifier l’absence d’effet avant l’accord et le comportement actuel depuis l’interface.
- [x] Utiliser une recherche de titres commune à l’API, au MCP et à l’interface. Vérifier une recherche sans accent et la conservation du fil actif.

## Disponibilité du Podcast

- [x] Partager entre le Labo et tremplin_overview le prérequis audio OpenAI. Afficher la configuration à terminer et continuer à distinguer les modèles de dialogue.
- [x] Vérifier le cas d’un fournisseur de dialogue configuré sans OpenAI audio, puis le cas où la clé audio est disponible.

## Livraison

- [x] Régénérer OpenAPI et les types. Exécuter les contrôles, les tests ciblés et Playwright sur Edge avec des données et fournisseurs de recette. Faire une revue du lot.
- [x] Documenter les décisions, enregistrer les changements avec les hooks et publier codex/reorganisation sous l’identité locale Ruldane. Confirmer le SHA de la branche distante.
