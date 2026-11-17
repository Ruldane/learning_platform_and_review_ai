import type { components } from "@/shared/api/schema";

/** L'utilisateur connecté (`GET /auth/me`) ; ici, seul `auth_mode` compte. */
export type Me = components["schemas"]["MeOut"];

/** Le mode du back où « Tout supprimer » ferme aussi la session. */
export const GOOGLE_MODE = "google";
