import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";

/** Displayed name of a write author: `user` becomes « Toi », an agent keeps its name. */
export function authorLabel(slug: string): string {
  return slug === "user" ? t("memory.author.user") : agentIdentity(slug).name;
}
