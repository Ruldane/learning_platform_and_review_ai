import { t, type MessageKey } from "@/shared/i18n/t";
import { auth } from "@/shared/i18n/messages/auth";

const KNOWN: ReadonlySet<string> = new Set(Object.keys(auth.errors));

/**
 * The French message for a `/login?error=<code>` code. A missing code says nothing; an
 * unknown code (or one forged in the address) gives the general message: the code is never shown.
 */
export function loginErrorMessage(code: string | null): string | null {
  if (!code) return null;
  const known = code !== "unknown" && KNOWN.has(code);
  return t(`auth.errors.${known ? code : "unknown"}` as MessageKey);
}
