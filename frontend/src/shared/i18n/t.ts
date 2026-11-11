import { fr } from "./fr";

type Leaves<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${Prefix}${K}` : Leaves<T[K], `${Prefix}${K}.`>;
}[keyof T & string];

/** Chemin pointé vers un texte de `fr` (ex. `"settings.keys.last4"`). */
export type MessageKey = Leaves<typeof fr>;

function lookup(key: MessageKey): string {
  let node: unknown = fr;
  for (const part of key.split(".")) {
    node =
      typeof node === "object" && node !== null
        ? (node as Record<string, unknown>)[part]
        : undefined;
  }
  return typeof node === "string" ? node : key;
}

/** Renvoie le texte français de `key`, en remplaçant chaque `{nom}` par `vars.nom`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  const message = lookup(key);
  if (!vars) return message;
  return message.replace(/\{(\w+)\}/g, (placeholder, name: string) => {
    const value = vars[name];
    return value === undefined ? placeholder : String(value);
  });
}
