/** Copie dans le presse-papiers ; une erreur (accès refusé, pas de presse-papiers) remonte à qui copie. */
export async function copyToClipboard(text: string): Promise<void> {
  if (!navigator.clipboard) throw new Error("clipboard unavailable");
  await navigator.clipboard.writeText(text);
}
