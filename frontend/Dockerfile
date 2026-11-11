# Étape 1 : construction du site statique.
# Le projet front est créé par la tâche 0.11 ; cette image est vérifiée par la tâche 0.14.
FROM node:22.22.3-alpine3.24 AS build

# L'adresse du back est figée dans le bundle au moment de la construction (Vite).
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

# corepack lit la version de pnpm dans le champ `packageManager` de package.json.
RUN corepack enable

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# Étape 2 : nginx sert dist/ sur le port 5173, avec repli SPA vers index.html.
FROM nginx:1.31.8-alpine3.24

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5173
