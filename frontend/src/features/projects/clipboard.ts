import { t } from "@/shared/i18n/t";

/**
 * Copies text to the clipboard. A rejected promise reports the failure (clipboard missing or
 * refused by the browser): `DraftCard` confirms « Brouillon copié. » only if it resolves.
 */
export async function copyText(text: string): Promise<void> {
  // Missing outside a secure context (http) or in an old browser.
  const clipboard = (navigator as { clipboard?: Clipboard }).clipboard;
  if (!clipboard || typeof clipboard.writeText !== "function") {
    throw new Error(t("projects.errors.clipboard"));
  }
  await clipboard.writeText(text);
}
