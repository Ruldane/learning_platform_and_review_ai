# Installer ou transférer Tremplin vers un autre PC

Le dépôt Git contient le code et les migrations. Le volume Docker `app_data`
contient la base SQLite, les points de reprise des agents, les fichiers
importés et la clé locale qui permet de déchiffrer les secrets stockés. Une
installation neuve peut démarrer avec une base vide. Un transfert requiert une
copie cohérente de ce volume.

Les commandes ci-dessous s’exécutent depuis la racine du dépôt. Elles utilisent
le nom de projet Compose `learning_career_platform`, indépendamment du nom
du dossier. Docker doit fonctionner en mode conteneurs Linux.

## 1. Sauvegarder l’ancien PC

1. Créer un dossier neuf `tremplin-donnees` dans un emplacement privé, distinct
   du dépôt Git.
2. Arrêter le backend, copier son dossier `/data` entier, puis le redémarrer.
   L’exemple utilise un dossier frère du dépôt.

   ```sh
   docker compose -p learning_career_platform stop backend
   docker compose -p learning_career_platform cp backend:/data/. ../tremplin-donnees
   docker compose -p learning_career_platform start backend
   ```

3. Vérifier que la copie contient `app.db`, `checkpoints.db`, `secret.key`
   et `storage/`. Inclure les fichiers compagnons `-wal` et `-shm` présents.
   Garder la sauvegarde intacte jusqu’à validation du nouveau PC.
4. Transférer la sauvegarde par un canal privé. Stocker le fichier de configuration
   `.env` ou recréer ses valeurs sur le nouveau PC par un canal séparé. La base,
   les fichiers personnels, `.env` et `secret.key` restent hors de GitHub.

Qdrant et Ollama ont leurs propres volumes. Sur un nouveau PC, Tremplin peut
reconstruire l’index Qdrant depuis les textes de la base. Ollama peut
retélécharger son modèle d’embeddings.

## 2. Récupérer le code et configurer le nouveau PC

Cloner le dépôt GitHub, sélectionner la branche publiée souhaitée et ouvrir
la racine. `git log -1 --oneline` permet de relever la version qui sera installée.
Créer `.env` sur le nouveau PC à partir du fichier d’exemple s’il est
présent. Renseigner `OPENAI_API_KEY` en local et reprendre les ports souhaités.

Construire les trois images. Avec le port API par défaut, utiliser ces commandes.
Si `BACKEND_PORT` vaut autre chose, reprendre cette valeur dans `VITE_API_URL`
à la construction du frontend.

```sh
docker build -t learning_career_platform-backend:latest backend
docker build --build-arg VITE_API_URL=http://localhost:8000 -t learning_career_platform-frontend:latest frontend
docker build -t learning_career_platform-sandbox:latest sandbox
```

Pour une base neuve, passer directement à l’étape 4.

## 3. Restaurer dans un volume neuf

Vérifier les volumes avant de créer la pile.

```sh
docker volume ls --filter label=com.docker.compose.project=learning_career_platform
```

Pour un transfert sur un PC qui héberge déjà Tremplin, prendre d’abord une
sauvegarde de cette installation. Utiliser un projet Compose distinct et ses
images nommées en conséquence pour tester la restauration dans un volume neuf.
Configurer des ports distincts si les deux piles tournent ensemble.

Sur un PC neuf, créer le conteneur backend sans le démarrer. Placer le dossier
de sauvegarde à côté de la racine ou ajuster son chemin dans la commande
`cp`. L’option `--no-deps` limite cette préparation au backend.

```sh
docker compose -p learning_career_platform up --no-start --no-build --no-deps backend
docker compose -p learning_career_platform cp ../tremplin-donnees/. backend:/data
docker compose -p learning_career_platform run --rm --no-deps --user 0 --entrypoint chown backend -R app:app /data
```

Copier la base, ses fichiers compagnons et la clé ensemble avant le premier
démarrage. Le backend pourra alors lire les écritures SQLite récentes et
déchiffrer les réglages transférés.

## 4. Démarrer et contrôler la migration

```sh
docker compose -p learning_career_platform up -d --no-build
docker compose -p learning_career_platform ps -a
docker compose -p learning_career_platform exec -T backend alembic current
docker compose -p learning_career_platform exec -T backend alembic heads
```

Le backend applique `alembic upgrade head` à son démarrage. La révision
courante doit correspondre à la tête de l’image. Vérifier l’API à
`http://localhost:8000/api/v1/health`, ou sur le port configuré, puis ouvrir
l’interface sur le port `FRONTEND_PORT` (5173 par défaut).

1. Dans **Apprendre**, vérifier les programmes, les leçons et quelques fichiers
   par rapport à la sauvegarde. Le jeu transféré d’origine comptait quatre
   programmes et 123 leçons.
2. Dans **Réglages > Modèles et clés**, vérifier que les niveaux sont réglés
   sur OpenAI. Une clé saisie auparavant dans l’interface prime sur la
   clé du même fournisseur dans `.env`.
3. Dans **Mémoire**, choisir **Réindexer** après le téléchargement de `bge-m3`.
   Attendre la fin de l’indexation et vérifier une recherche en mémoire.
4. Pour reconnecter un client MCP, créer son jeton dans **Réglages > Accès
   MCP** et suivre le [guide MCP](mcp/AGENTS.md). Conserver le jeton dans une
   variable locale du client.

## En cas d’échec

```sh
docker compose -p learning_career_platform logs --tail 60 backend ollama-init
```

Si Alembic échoue, relever la révision et l’erreur avant de relancer. Garder la
sauvegarde intacte. Une nouvelle tentative de restauration peut partir d’une
autre copie et d’un volume neuf. Si le problème concerne les anciennes clés,
vérifier la présence de `secret.key` avec la base correspondante avant de
modifier les réglages.

Sous Windows, le [guide du dépôt](../AGENTS.md) indique les commandes Node et
la configuration Edge utilisées lorsque le contrôle d’applications bloque
les exécutables Playwright ou pnpm.

## Reprendre le projet avec Claude Code

Sur le nouveau PC, utiliser le nom de la branche livrée et comparer le
commit affiché à celui de la livraison.

```sh
git clone --branch "<branche livrée>" "https://github.com/Ruldane/learning_platform_and_review_ai.git" Tremplin
cd Tremplin
git rev-parse HEAD
```

Pour créer des commits depuis ce PC, configurer l’identité sur ce dépôt.

```sh
git config --local user.name "Ruldane"
git config --local user.email "l.nizzoli@gmail.com"
```

Si le dépôt existe déjà, garder une trace du travail local avec
`git status --short`. Récupérer la branche publiée avec `git fetch origin`.
Une branche locale neuve peut ensuite suivre la livraison avec
`git switch --track "origin/<branche livrée>"`. Une branche locale déjà créée
peut avancer par `git pull --ff-only` quand elle suit la bonne branche distante.

Texte à donner à Claude Code, avec les mêmes valeurs et le chemin du transfert.

> Reprends Tremplin sur ce PC à partir du dépôt GitHub « <URL du dépôt> »,
> branche « <branche livrée> », commit « <commit livré> ». Vérifie le commit
> local et lis AGENTS.md, CLAUDE.md et docs/INSTALLATION-ET-MIGRATION.md.
> Préserve mes modifications locales et les volumes existants. Le dossier
> de sauvegarde est « <chemin de tremplin-donnees> ». Prépare un volume neuf,
> restaure la base SQLite, les points de reprise et les fichiers ensemble,
> puis vérifie la révision Alembic, les programmes, les leçons et la mémoire.
> La configuration privée reste dans .env et la plateforme utilise OpenAI.
> Vérifie le démarrage local et donne les résultats sans afficher de clé.
