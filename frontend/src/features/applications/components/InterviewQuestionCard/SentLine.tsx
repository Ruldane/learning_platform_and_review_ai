import { t } from "@/shared/i18n/t";

/** Ce que January a envoyé : sa réponse, ou la fin de l'entretien. */
export type Sent = { kind: "answer"; text: string } | { kind: "stop" };

/** Ce que la carte repliée rappelle : la réponse envoyée, ou la fin de l'entretien. */
export function SentLine({ sent }: { sent: Sent | null }) {
  if (sent === null) return null;
  return sent.kind === "answer" ? (
    <p className="whitespace-pre-wrap">{sent.text}</p>
  ) : (
    <p>{t("applications.interviewRun.stopped")}</p>
  );
}
