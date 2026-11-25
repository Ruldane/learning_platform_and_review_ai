/**
 * TanStack Query keys read here. `me` is the key of the signed-in user, set by the login gate
 * (feature `auth`): one feature does not import another, so the key is repeated here
 * (a `DataPage` test keeps it in sync).
 */
export const accountKeys = {
  me: ["auth", "me"],
} as const;

/** The `auth` feature's queries: « Mes données » never clears the identity through this path. */
export const AUTH_SCOPE = "auth";
