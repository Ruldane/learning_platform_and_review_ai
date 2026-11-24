import { apiBaseUrl } from "@/shared/api/client";

/** Adresses internes des candidatures : les pages de 7.14 à 7.16 y sont déjà promises. */
export const BOARD_PATH = "/applications";
export const REMINDERS_PATH = "/applications/reminders";
export const NEW_APPLICATION_PATH = "/applications/new";
export const FREE_INTERVIEW_PATH = "/applications/interview";

export const applicationPath = (applicationId: string) => `${BOARD_PATH}/${applicationId}`;
export const kitPath = (applicationId: string) => `${applicationPath(applicationId)}/kit`;
export const interviewPath = (applicationId: string) =>
  `${applicationPath(applicationId)}/entretien`;
export const committeePath = (applicationId: string) => `${applicationPath(applicationId)}/comite`;

/** Les versions de CV (la page de la feature `cv`) : la fiche y renvoie pour la version envoyée. */
export const CV_VERSIONS_PATH = "/career/cv/versions";

/** `GET /applications/{id}/kit.zip` : l'archive du kit (les pièces, le PDF du CV, un LISEZMOI). */
export const kitZipUrl = (applicationId: string) =>
  `${apiBaseUrl}/api/v1/applications/${applicationId}/kit.zip`;

/** Les révisions (la page des fiches, feature `quiz`) : les fiches d'un entretien y attendent. */
export const REVISIONS_PATH = "/study/reviews";

/** Le profil maître validé (la page de la feature `cv`) : le kit part de lui. */
export const PROFILE_PATH = "/career/profile";
