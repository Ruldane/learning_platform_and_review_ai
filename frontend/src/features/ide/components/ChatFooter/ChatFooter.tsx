import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";

interface ChatFooterProps {
  /** Le professeur écrit. */
  typing: boolean;
  /** Pourquoi rien n'est parti, ou l'erreur. */
  notice: { tone: "status" | "error"; text: string } | null;
}

/** Sous le dernier message : « Le professeur écrit… », la raison d'un refus, l'erreur. */
export function ChatFooter({ typing, notice }: ChatFooterProps) {
  return (
    <>
      {typing ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("ide.teacher.thinking")}
        </p>
      ) : null}
      {notice?.tone === "error" ? <InlineError message={notice.text} /> : null}
      {notice?.tone === "status" ? (
        <p role="status" className="text-sm">
          {notice.text}
        </p>
      ) : null}
    </>
  );
}
