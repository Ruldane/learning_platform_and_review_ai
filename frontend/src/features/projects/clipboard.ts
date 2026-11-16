import { t } from "@/shared/i18n/t";

/**
 * Copie un texte dans le presse-papiers. Une promesse rejetée dit l'échec (presse-papiers absent ou
 * refus du navigateur) : `DraftCard` ne confirme « Brouillon copié. » que si elle se résout.
 */
export async function copyText(text: string): Promise<void> {
  // Absent hors contexte sécurisé (http) ou dans un navigateur ancien.
  const clipboard = (navigator as { clipboard?: Clipboard }).clipboard;
  if (!clipboard || typeof clipboard.writeText !== "function") {
    throw new Error(t("projects.errors.clipboard"));
  }
  await clipboard.writeText(text);
}
