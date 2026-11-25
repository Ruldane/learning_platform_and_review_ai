/** Copies to the clipboard; an error (access denied, no clipboard) is passed back to the caller. */
export async function copyToClipboard(text: string): Promise<void> {
  if (!navigator.clipboard) throw new Error("clipboard unavailable");
  await navigator.clipboard.writeText(text);
}
