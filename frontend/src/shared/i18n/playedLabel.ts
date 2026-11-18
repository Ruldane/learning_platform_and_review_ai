import { t } from "./t";

export function playedLabel(client: string | null | undefined): string | undefined {
  if (client === "codex") return t("session.played.codex");
  if (client === "claude-code") return t("session.played.claude");
  return undefined;
}
