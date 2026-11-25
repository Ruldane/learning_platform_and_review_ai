import { apiBaseUrl } from "@/shared/api/client";

const cvUrl = (path: string) => `${apiBaseUrl}/api/v1/cv${path}`;

/** The PDF of a version (download: the `CV_….pdf` name comes from the server header). */
export const versionPdfUrl = (versionId: string) => cvUrl(`/versions/${versionId}/pdf`);

/** The image of page `n` (from 1) of a ready version. */
export const versionPageUrl = (versionId: string, n: number) =>
  cvUrl(`/versions/${versionId}/pages/${n}`);

/**
 * The image of page `n` of the original CV or of a template's current pass render. `pass`
 * changes on each pass, so the browser does not keep the old image.
 */
export const templatePageUrl = (
  templateId: string,
  kind: "original" | "render",
  n: number,
  pass: number,
) => cvUrl(`/templates/${templateId}/pages/${kind}/${n}?pass=${pass}`);

/** The URLs of pages `1..count` of one document. */
export const pageRange = (count: number, url: (n: number) => string): string[] =>
  Array.from({ length: Math.max(count, 0) }, (_, index) => url(index + 1));
