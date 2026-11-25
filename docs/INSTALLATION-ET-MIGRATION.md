# Install Tremplin or move it to another PC

The Git repository contains the code and migrations. The Docker volume `app_data`
holds the SQLite database, agent checkpoints, imported files, and the local key
that decrypts saved secrets. A fresh installation can start with an empty database.
A transfer requires a consistent copy of the volume.

Run the commands from the repository root. They use the Compose project name
`learning_career_platform` regardless of the folder name. Docker must be in Linux
container mode.

## 1. Back up the original PC

1. Create a new private folder named `tremplin-data` outside the Git repository.
2. Stop the backend, copy its entire `/data` directory, and restart it. The following
   commands use a backup folder beside the repository.

   ```sh
   docker compose -p learning_career_platform stop backend
   docker compose -p learning_career_platform cp backend:/data/. ../tremplin-data
   docker compose -p learning_career_platform start backend
   ```

3. Check for `app.db`, `checkpoints.db`, `secret.key`, and `storage/`. Include any
   `-wal` and `-shm` companion files. Keep this backup until you verify the new PC.
4. Transfer the backup privately. Recreate the settings in `.env` on the new PC,
   keeping that configuration separate from the backup. Keep the databases,
   personal files, `.env`, and `secret.key` out of GitHub.

Qdrant and Ollama use separate volumes. On a new PC, Tremplin can rebuild its
Qdrant index from the database text. Ollama can download the embedding model again.

## 2. Get the code and configure the new PC

Clone the repository, select the published branch you want, and open the repository
root. Record the version with `git log -1 --oneline`. Create a local `.env` from the
example file if available, then enter your `OPENAI_API_KEY` and any port settings.

Build all three images. The example uses the default API port. If you change
`BACKEND_PORT`, use the same port in `VITE_API_URL` when building the frontend.

```sh
docker build -t learning_career_platform-backend:latest backend
docker build -t learning_career_platform-frontend:latest \
  --build-arg VITE_API_URL=http://localhost:8000 frontend
docker build -t learning_career_platform-sandbox:latest sandbox
```

For a fresh database, continue to step 4.

## 3. Restore to a new volume

Check the volumes before creating the stack.

```sh
docker volume ls --filter label=com.docker.compose.project=learning_career_platform
```

If the destination already runs Tremplin, back up that installation first.
Use a separate Compose project with matching image names to try the restore in
a new volume. Set different ports if both stacks will run at once.

On a new PC, create the backend container without starting it. Place the backup
folder beside the repository or adjust the path in the copy command. The
`--no-deps` flag limits this preparation to the backend.

```sh
docker compose -p learning_career_platform up --no-start --no-build --no-deps backend
docker compose -p learning_career_platform cp ../tremplin-data/. backend:/data
docker compose -p learning_career_platform run --rm --no-deps --user 0 \
  --entrypoint chown backend -R app:app /data
```

Restore the database, its companion files, and its key together before the
first start. This lets the backend read recent SQLite writes and decrypt the
transferred settings.

## 4. Start the app and verify the migration

```sh
docker compose -p learning_career_platform up -d --no-build
docker compose -p learning_career_platform ps -a
docker compose -p learning_career_platform exec -T backend alembic current
docker compose -p learning_career_platform exec -T backend alembic heads
```

The conversation migration assigns titles to older Brain and Study threads
from their first message. It keeps the thread IDs and saved learning data.
Before retiring the backup, check an older thread on each page and open a flashcard.

The backend runs `alembic upgrade head` at startup. The current revision should match
the image's head revision. Check `http://localhost:8000/api/v1/health` on the configured
API port, then open the app on `FRONTEND_PORT`, which defaults to 5173.

1. In **Learn**, compare programs, lessons, and a few files with the backup. The
   original transfer contained four programs and 123 lessons.
2. In **Settings > Models and keys**, verify the expected provider and model for
   each tier. A key entered in the app takes precedence over that provider's key in
   `.env`. The original transfer used OpenAI.
3. In **Memory**, select **Reindex** once Ollama has downloaded `bge-m3`.
   Wait for indexing to finish and try a memory search.
4. To reconnect an MCP client, create its token in **Settings > MCP access**
   and keep the token in a local environment variable for the client.
   [MCP guide](mcp/AGENTS.md)

## Troubleshooting

```sh
docker compose -p learning_career_platform logs --tail 60 backend ollama-init
```

If Alembic fails, record the revision and error before retrying. Keep the
backup intact and use another copy and a fresh volume for a second attempt.
If saved keys cannot be decrypted, check that `secret.key` came from the same
backup as the database before changing settings.

On Windows, the repository guide covers the Node commands and Edge configuration
for machines where Smart App Control blocks the Playwright or pnpm executables.
[Repository guide](../AGENTS.md)

## Resume development with Claude Code

On the new PC, use the published branch and compare the local commit with the
published commit.

```sh
git clone --branch "<published branch>" \
  "https://github.com/Ruldane/learning_platform_and_review_ai.git" Tremplin
cd Tremplin
git rev-parse HEAD
```

Before committing from this PC, configure the repository's Git identity.

```sh
git config --local user.name "Ruldane"
git config --local user.email "l.nizzoli@gmail.com"
```

If the repository is already present, check local changes with
`git status --short` and fetch the published branch with `git fetch origin`.
Create a local tracking branch with `git switch --track "origin/<published branch>"`.
For an existing branch that tracks the correct remote, use `git pull --ff-only`.

Give Claude Code the repository and backup details for the transfer.

> Resume Tremplin on this PC from GitHub repository "<repository URL>", branch
> "<published branch>", and commit "<published commit>". Check the local commit
> and read AGENTS.md, CLAUDE.md, and docs/INSTALLATION-ET-MIGRATION.md.
> Preserve my local changes and existing volumes. The backup is in
> "<path to tremplin-data>". Prepare a fresh volume and restore the SQLite
> database, checkpoints, and files together. Check the Alembic revision,
> programs, lessons, and memory.
> Leave private configuration in .env. This installation uses OpenAI.
> Verify local startup and report the results without displaying any key.
