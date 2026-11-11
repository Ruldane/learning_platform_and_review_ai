import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";

/** Nom affiché d'un auteur d'écriture : `user` devient « Toi », un agent garde son nom. */
export function authorLabel(slug: string): string {
  return slug === "user" ? t("memory.author.user") : agentIdentity(slug).name;
}
