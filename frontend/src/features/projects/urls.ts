import { apiBaseUrl } from "@/shared/api/client";

/**
 * The address of a submission screenshot (`GET /projects/{id}/screenshots/{n}?submission=`):
 * `number` from 1 to 5, `submission` 1 for the latest, 2 for the one before. Images load
 * a header: the address is enough for `<img>`.
 */
export const screenshotUrl = (projectId: string, number: number, submission: number): string =>
  `${apiBaseUrl}/api/v1/projects/${projectId}/screenshots/${number}?submission=${submission}`;
