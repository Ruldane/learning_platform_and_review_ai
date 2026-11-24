import { t, type MessageKey } from "@/shared/i18n/t";
import { auth } from "@/shared/i18n/messages/auth";

const KNOWN: ReadonlySet<string> = new Set(Object.keys(auth.errors));

/**
 * Le message français d'un code de `/login?error=<code>`. Un code absent ne dit rien ; un
 * code inconnu (ou forgé dans l'adresse) donne le message général : le code n'est jamais affiché.
 */
export function loginErrorMessage(code: string | null): string | null {
  if (!code) return null;
  const known = code !== "unknown" && KNOWN.has(code);
  return t(`auth.errors.${known ? code : "unknown"}` as MessageKey);
}
