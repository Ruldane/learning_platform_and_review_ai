# Tremplin

Plateforme locale d'apprentissage et de carrière, pilotée par plusieurs agents IA. Elle tourne
entièrement sous Docker sur votre machine : backend FastAPI, frontend React, base vectorielle,
modèles locaux optionnels.

Documents de référence : [SPEC.md](SPEC.md) (la spec), [DECISIONS.md](DECISIONS.md) (les choix et
écarts), `docs/superpowers/plans/` (les plans d'implémentation).

## Prérequis

- Docker et Docker Compose **2.24 ou plus récent** (`env_file` avec `required: false`) :
  `docker compose version` pour vérifier.
- [uv](https://docs.astral.sh/uv/) (Python 3.12 géré par uv), pour développer le back.
- Node.js 22 ou plus et pnpm (`corepack enable`), pour développer le front.

## Démarrage

```bash
cp .env.example .env     # y coller une seule clé LLM (ou la saisir plus tard dans l'interface)
docker compose up -d
# ouvrir http://localhost:5173
```

Une seule clé suffit (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` ou `ZAI_API_KEY`) ; `BRAVE_API_KEY`
est facultative. Les autres variables de `.env.example` ont toutes un défaut qui convient :
elles servent à changer un port, à brancher un Ollama installé sur la machine ou à activer la
connexion Google (voir plus bas).

- Le premier démarrage construit les images et télécharge le modèle d'embeddings `bge-m3`
  (environ 1,2 Go) : `docker compose logs -f ollama-init` montre la progression, le service
  s'arrête une fois le modèle en place. L'application répond pendant ce temps.
- Au premier lancement, l'application t'accueille en cinq étapes : l'état des services avec la
  progression du téléchargement de `bge-m3`, ce qui sort de ta machine, ta clé d'API (avec un
  test), l'import de ton CV et de ton profil LinkedIn (tu peux passer), puis ta disponibilité.
  Elle ne revient pas une fois terminée. La progression de `bge-m3` est aussi lisible sans
  l'interface : `curl -s http://localhost:8000/api/v1/health/embedding` (public, comme `/health`)
  rend `present`, `percent` (de 0 à 100) et un texte. Si le modèle manque, le back le télécharge
  lui-même depuis Ollama, une seule fois à la fois.
- État des services : `curl -s http://localhost:8000/api/v1/health` (ou le voyant en haut de
  l'interface). `"status": "ok"` quand la base, les 4 services et au moins une clé LLM sont là ;
  `"degraded"` détaille ce qui manque.
- Les clés API se saisissent aussi dans **Réglages > Modèles et clés** : elles sont chiffrées dans
  le volume `app_data`, seuls leurs 4 derniers caractères sont affichés, et une clé saisie dans
  l'interface prime sur celle du `.env`.
- Arrêt : `docker compose down` (les volumes `app_data`, `qdrant_data`, `ollama_data` sont
  conservés ; `docker compose down -v` efface toutes les données).

### Ports déjà pris

Les ports publiés (sur `127.0.0.1` seulement) sont 5173 (interface), 8000 (API) et 6333
(Qdrant). Si l'un est déjà utilisé par un autre projet, le choisir dans `.env` :

```bash
FRONTEND_PORT=5174
BACKEND_PORT=8001
QDRANT_PORT=6335
```

puis `docker compose up -d --build` (l'adresse de l'API est intégrée à l'interface à la
construction). L'origine autorisée par le back (`CORS_ORIGIN`) suit `FRONTEND_PORT`, et
l'interface est alors sur `http://localhost:<FRONTEND_PORT>` (ou `http://127.0.0.1:<FRONTEND_PORT>` :
les deux formes d'une origine locale sont acceptées). Pour autoriser d'autres origines (un front
lancé hors Docker, par exemple), donner dans `.env` la liste complète, séparée par des virgules :
`CORS_ORIGIN=http://localhost:5174,http://localhost:4173`.

### macOS et Ollama installé sur la machine

Docker n'a pas accès au GPU sous macOS. Pour utiliser l'Ollama de la machine, décommenter
`OLLAMA_BASE_URL=http://host.docker.internal:11434` dans `.env`, puis télécharger le modèle sur
la machine, car `ollama-init` le télécharge dans le conteneur et non dans votre Ollama :

```bash
ollama pull bge-m3
```

### Windows

Si `docker compose build` échoue avec « additional privileges requested », définir
`BUILDX_BAKE_ENTITLEMENTS_FS=0` (Git Bash : `export BUILDX_BAKE_ENTITLEMENTS_FS=0`).

### Variables de `.env`

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ZAI_API_KEY` | Clé du fournisseur LLM (une seule suffit) | vide |
| `BRAVE_API_KEY` | Recherche web Brave (facultatif) | vide |
| `AUTH_MODE` | `local` (un utilisateur, sans connexion) ou `google` | `local` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Client OAuth Google (mode Google) | vide |
| `ALLOWED_EMAILS` | Adresses autorisées en mode Google (voir plus bas) | vide |
| `GOOGLE_REDIRECT_URI`, `FRONTEND_URL` | Adresse de retour de Google et adresse du front | suivent `BACKEND_PORT` et `FRONTEND_PORT` |
| `OLLAMA_BASE_URL` | Ollama de la machine plutôt que celui de Docker | `http://ollama:11434` |
| `ZAI_BASE_URL` | Adresse de l'API Z.ai | `https://api.z.ai/api/paas/v4/` |
| `LLM_CALL_DEADLINE_S` | Échéance totale d'un appel à un modèle, en secondes | `600` |
| `WEB_RENDER_FALLBACK` | Repli Gotenberg du lecteur web ; `false` le coupe | `true` |
| `FRONTEND_PORT`, `BACKEND_PORT`, `QDRANT_PORT` | Ports publiés sur `127.0.0.1` | `5173`, `8000`, `6333` |
| `CORS_ORIGIN` | Origine(s) du front autorisée(s) par le back | suit `FRONTEND_PORT` |

Les clés ne sont jamais renvoyées au navigateur ni écrites dans les journaux, et `.env` n'est
jamais commité.

## Mode Google : un compte par personne

Par défaut (`AUTH_MODE=local`), l'application n'a qu'un seul utilisateur et aucune page de
connexion. Pour la partager à quelques personnes, chacune avec son espace, active la connexion
Google. Elle demande de créer un client OAuth dans la console Google : c'est la seule
configuration au delà des clés d'API.

1. **Projet.** Sur <https://console.cloud.google.com>, crée un projet (« Tremplin », par exemple).
2. **Écran de consentement** (Google Auth Platform, ou « APIs et services > Écran de consentement
   OAuth ») : type d'utilisateur **Externe**, nom de l'application, adresse d'assistance. Les
   portées demandées sont `openid`, `email` et `profile` seulement. Tant que l'application est
   « en test », ajoute chaque adresse comme **utilisateur test** ; tu peux aussi la publier
   (ces portées de base ne demandent pas de validation par Google).
3. **Identifiants > Créer des identifiants > ID client OAuth**, type **Application Web**, avec :
   - origine JavaScript autorisée : `http://localhost:5173` ;
   - URI de redirection autorisé : `http://localhost:8000/api/v1/auth/google/callback`.

   Copie l'ID client et le code secret. Si tu as changé `FRONTEND_PORT` ou `BACKEND_PORT`, reprends
   les mêmes ports dans ces deux adresses ; l'adresse de retour doit être **identique au
   caractère près** à `GOOGLE_REDIRECT_URI` (qui suit `BACKEND_PORT` par défaut).
4. **Variables** dans `.env` :

   ```bash
   AUTH_MODE=google
   GOOGLE_CLIENT_ID=<l'ID client>
   GOOGLE_CLIENT_SECRET=<le code secret>
   ALLOWED_EMAILS=camille.exemple@example.org,dominique.exemple@example.org
   # GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   # FRONTEND_URL=http://localhost:5173
   ```

   `GOOGLE_REDIRECT_URI` et `FRONTEND_URL` ne sont à écrire que si l'adresse n'est pas
   `http://localhost:<port>` (un autre nom d'hôte, ou `https`) : elles suivent déjà
   `BACKEND_PORT` et `FRONTEND_PORT`.
5. **`ALLOWED_EMAILS`** : liste séparée par des virgules, comparée en minuscules et sans tenir
   compte des espaces. **Vide, le back refuse de démarrer** en mode Google (message dans
   `docker compose logs backend`). `*` laisse entrer tous les comptes Google ; sinon seuls les
   comptes de la liste entrent. La liste est contrôlée à la connexion et à chaque requête :
   retirer une adresse du `.env` puis relancer le back (`docker compose up -d`) coupe l'accès de
   ce compte aussitôt.
6. `docker compose up -d`, puis **ouvre l'application par `http://localhost:5173`**, pas par
   `127.0.0.1` : le cookie de session est posé sur `localhost`, et le WebSocket des sessions
   d'agents exige ce cookie et un en-tête `Origin` de l'interface (un script hors navigateur doit
   donc l'envoyer).

La connexion est un code d'autorisation avec PKCE ; la session tient dans un cookie `HttpOnly`
`SameSite=Lax` de 30 jours (`Secure` quand l'adresse de retour est en `https`). Chaque ligne
de la base, chaque vecteur et chaque fichier porte l'identifiant de son propriétaire : deux
comptes ne voient jamais les données l'un de l'autre. Les clés d'API saisies dans l'interface
sont celles de chaque compte ; celles du `.env` servent à tous.

### Reprise de l'espace local

Si tu as déjà utilisé Tremplin en mode local, tes données sont dans l'espace `local`. Au premier
passage en mode Google, **seule une adresse nommée dans `ALLOWED_EMAILS`** se voit proposer de
**reprendre** cet espace (rien n'est déplacé : le compte Google prend la place de l'utilisateur
local) ou de commencer avec un **espace vide** (l'espace local reste intact en base, visible
en repassant en `AUTH_MODE=local`). Règles à connaître :

- Avec `*`, la reprise n'est **jamais** proposée : la première personne venue prendrait des
  données qui ne sont pas les siennes. Pour reprendre l'espace local, nomme ton adresse dans la
  liste.
- Avec **plusieurs adresses nommées, la première qui se connecte prend l'espace local** (ou le
  refuse en choisissant « Espace vide »). Dès qu'un compte Google existe, la reprise n'est plus
  proposée à personne d'autre.
- Si le premier compte choisit « Espace vide » puis « Tout supprimer » (voir plus bas), son
  compte disparaît : l'espace local, resté en base, est de nouveau proposé à la prochaine
  adresse nommée qui se connecte.

## Export et suppression de tes données

Dans **Réglages > Mes données** :

- **Exporter toutes mes données** : une archive `tremplin-export-AAAAMMJJ.zip` avec un
  `manifest.json` (date, nombre de lignes par table, nombre de fichiers), un fichier JSON par
  table et les fichiers que tu as importés. Elle ne contient ni tes clés d'API, ni les vecteurs
  de la mémoire (recalculés à partir du texte), ni les points de reprise des agents.
- **Tout supprimer** : efface tes lignes, tes vecteurs, tes fichiers et les points de reprise de
  tes sessions, après confirmation en tapant `SUPPRIMER`. En mode local l'application reste
  utilisable, avec un espace vide ; en mode Google ton compte disparaît aussi et tu reviens à la
  page de connexion. Les clés du `.env` ne sont pas touchées. Si le service de vecteurs est en
  panne, l'opération s'arrête et peut être relancée jusqu'au bout.

## Ce qui sort de la machine

| Donnée | Destination |
| --- | --- |
| Prompts, qui peuvent contenir le CV et le profil | Le fournisseur LLM choisi |
| Requêtes de recherche | Les moteurs interrogés par SearXNG |
| Tout le reste (base, vecteurs, fichiers, embeddings) | Reste en local |

Le bouton **Tester** d'une clé et la liste des modèles appellent le fournisseur concerné avec
cette clé. En mode Google, la connexion passe par Google, qui apprend que tu ouvres Tremplin ;
l'application reçoit seulement ton adresse et ton nom. Le modèle d'embeddings `bge-m3` est
téléchargé une fois depuis le registre d'Ollama. Aucune autre donnée ne quitte la machine : nom,
adresse et téléphone sont retirés des requêtes de recherche avant leur envoi.

## Coûts

- Gratuit et local : Qdrant, `bge-m3` (Ollama), SearXNG et Gotenberg.
- Payant à l'usage : les appels aux modèles du fournisseur dont tu as saisi la clé (Anthropic,
  OpenAI ou Z.ai). Brave est facultatif.
- L'écran **Coûts** des réglages totalise les dépenses par jour, par fonction, par agent et par
  modèle sur 7, 30 ou 90 jours, et le **journal des agents** liste chaque appel (agent, modèle,
  jetons, durée, coût). Les prix viennent de `backend/app/providers/llm/model_prices.json`, tels
  qu'ils étaient au moment de l'appel : ce sont des estimations, pas une facture.
- Les réglages permettent de choisir un modèle moins cher par niveau, ou agent par agent (mode
  avancé).

## Services

- Les 7 services : `frontend` (5173), `backend` (8000), `qdrant` (6333), `ollama`, `ollama-init`
  (télécharge `bge-m3` une fois, puis s'arrête), `searxng`, `gotenberg`. Volumes nommés :
  `app_data`, `qdrant_data`, `ollama_data`.
- Le back démarre dès que les 4 services sont sains, sans attendre `bge-m3`.
- Les versions des images sont figées dans `docker-compose.yml` (voir DECISIONS.md, D30).

## Développement

Rechargement à chaud du back et du front dans Docker :

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Développement du back

```bash
cd backend
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python -m mypy app
uv run lint-imports                          # contrats d'import (pyproject.toml)
uv run python -m scripts.export_openapi      # régénère contracts/openapi.json
```

Lancement hors Docker (données dans `backend/data/`, ignoré par git) :

```bash
mkdir -p data && export DATA_DIR=./data
uv run alembic upgrade head
uv run uvicorn --factory app.main:create_app --reload
```

## Développement du front

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:5173, API attendue sur http://localhost:8000
pnpm test && pnpm lint && pnpm typecheck && pnpm build
pnpm gen:api      # types TypeScript depuis contracts/openapi.json
```

## Contrôles de qualité

Installation des hooks (une fois, depuis la racine du dépôt) :

```bash
uv run --project backend python -m pre_commit install
```

Exécution manuelle sur tout le dépôt :

```bash
uv run --project backend python -m pre_commit run --all-files
```

Règles de taille : 300 lignes par fichier et 50 par fonction, vérifiées par
`backend/scripts/check_file_length.py`. Les frontières d'architecture sont vérifiées par
import-linter (back) et `eslint-plugin-boundaries` (front). Sous Windows, certains exécutables
(`mypy.exe`, `pre-commit.exe`) peuvent être bloqués : les appeler en module (`python -m ...`).

## Parcours de bout en bout

Cinq parcours Playwright (depuis `frontend/`), sur le back de bout en bout (`tests.e2e.server` :
la vraie application, des fournisseurs factices et des modèles scriptés, sans réseau ni LLM
réel) : `pnpm e2e` joue les quatre parcours du mode local (Conseil, CV, candidatures,
quotidien). Le cinquième (connexion, reprise de l'espace local, premier lancement, isolation,
export et suppression) a sa propre configuration, `playwright.auth.config.ts`, avec le back en
mode Google et un faux fournisseur d'identité. Ce faux fournisseur connecte n'importe quelle
adresse sans mot de passe : le serveur de ces essais refuse donc, en mode Google, d'écouter
ailleurs que sur `127.0.0.1`, `::1` ou `localhost`.

## Mettre à jour depuis une version précédente

```bash
git pull
docker compose up -d --build
```

Les données (volumes `app_data`, `qdrant_data`, `ollama_data`) sont conservées. À chaque
démarrage, le conteneur du back lance `alembic upgrade head` avant le serveur : la base est
migrée toute seule, et un back qui n'arrive pas à la migrer ne démarre pas
(`docker compose logs backend`). Les réglages déjà enregistrés comptent comme « premier
lancement terminé » : l'écran d'accueil ne s'impose pas à un compte existant. Pour garder une
copie avant une mise à jour : `docker compose cp backend:/data ./sauvegarde-tremplin`.
