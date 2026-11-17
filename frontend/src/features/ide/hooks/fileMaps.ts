export type Files = Record<string, string>;

/** Les fichiers de `names` seulement. */
export const pick = (files: Files, names: string[]): Files =>
  Object.fromEntries(Object.entries(files).filter(([name]) => names.includes(name)));

/** Tous les fichiers sauf ceux de `names`. */
export const omit = (files: Files, names: string[]): Files =>
  Object.fromEntries(Object.entries(files).filter(([name]) => !names.includes(name)));
