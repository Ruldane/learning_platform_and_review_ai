import { apiBaseUrl } from "@/shared/api/client";

/** Internal routes for applications and their tools. */
export const BOARD_PATH = "/applications";
export const REMINDERS_PATH = "/applications/reminders";
export const NEW_APPLICATION_PATH = "/applications/new";
export const FREE_INTERVIEW_PATH = "/applications/interview";

export const applicationPath = (applicationId: string) => `${BOARD_PATH}/${applicationId}`;
export const kitPath = (applicationId: string) => `${applicationPath(applicationId)}/kit`;
export const interviewPath = (applicationId: string) =>
  `${applicationPath(applicationId)}/interview`;
export const committeePath = (applicationId: string) =>
  `${applicationPath(applicationId)}/committee`;

/** Résumé versions are linked from the application that used them. */
export const CV_VERSIONS_PATH = "/career/cv/versions";

/** The kit archive contains the generated pieces, résumé PDF, and README. */
export const kitZipUrl = (applicationId: string) =>
  `${apiBaseUrl}/api/v1/applications/${applicationId}/kit.zip`;

/** Review cards from a practice interview appear here. */
export const REVISIONS_PATH = "/study/reviews";

/** The kit uses the validated master profile. */
export const PROFILE_PATH = "/career/profile";
