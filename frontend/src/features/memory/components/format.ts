/** Maximum upload size, matching the server's limit. */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** Extensions accepted for document imports. */
export const UPLOAD_EXTENSIONS = [".pdf", ".docx", ".md", ".markdown", ".txt"] as const;

const PERCENT = new Intl.NumberFormat("en-GB", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** Format the share as a percentage to one decimal place. */
export function formatShare(share: number): string {
  return PERCENT.format(share);
}
