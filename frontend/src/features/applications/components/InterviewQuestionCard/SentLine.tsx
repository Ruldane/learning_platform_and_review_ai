import { t } from "@/shared/i18n/t";

/** What January sent: the answer, or the end of the interview. */
export type Sent = { kind: "answer"; text: string } | { kind: "stop" };

/** What the folded card recalls: the answer sent, or the end of the interview. */
export function SentLine({ sent }: { sent: Sent | null }) {
  if (sent === null) return null;
  return sent.kind === "answer" ? (
    <p className="whitespace-pre-wrap">{sent.text}</p>
  ) : (
    <p>{t("applications.interviewRun.stopped")}</p>
  );
}
