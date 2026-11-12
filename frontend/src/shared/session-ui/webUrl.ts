/** L'adresse d'une page web (http ou https), ou `null` : jamais de lien `javascript:` ou `data:`. */
export function webUrl(url: string): URL | null {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed : null;
  } catch {
    return null;
  }
}
