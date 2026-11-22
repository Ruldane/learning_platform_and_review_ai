export function mergeVoiceDraft(current: string, transcript: string, limit = 4000): string {
  if (current.length >= limit) return current;
  const separator = current.trim() ? "\n\n" : "";
  return current + (separator + transcript).slice(0, limit - current.length);
}
