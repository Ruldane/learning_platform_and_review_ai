import { en } from "./en";

type Leaves<T, Prefix extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${Prefix}${K}` : Leaves<T[K], `${Prefix}${K}.`>;
}[keyof T & string];

/** Dotted path to a message, such as `"settings.keys.last4"`. */
export type MessageKey = Leaves<typeof en>;

function lookup(key: MessageKey): string {
  let node: unknown = en;
  for (const part of key.split(".")) {
    node =
      typeof node === "object" && node !== null
        ? (node as Record<string, unknown>)[part]
        : undefined;
  }
  return typeof node === "string" ? node : key;
}

/** Returns the English message for `key`, replacing each `{name}` with `vars.name`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  const message = lookup(key);
  if (!vars) return message;
  return message.replace(/\{(\w+)\}/g, (placeholder, name: string) => {
    const value = vars[name];
    return value === undefined ? placeholder : String(value);
  });
}
