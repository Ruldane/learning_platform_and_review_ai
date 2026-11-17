/**
 * Clés TanStack Query lues ici. `me` est la clé de l'utilisateur connecté, posée par la porte de
 * connexion (feature `auth`) : une feature n'en importe pas une autre, la clé est donc redite ici
 * (un test de `DataPage` la tient en accord).
 */
export const accountKeys = {
  me: ["auth", "me"],
} as const;

/** Les requêtes de la feature `auth` : « Mes données » ne vide jamais l'identité par ce chemin. */
export const AUTH_SCOPE = "auth";
