import type { components } from "@/shared/api/schema";

/** The signed-in user (`GET /auth/me`); here only `auth_mode` matters. */
export type Me = components["schemas"]["MeOut"];

/** The backend mode in which « Tout supprimer » also closes the session. */
export const GOOGLE_MODE = "google";
