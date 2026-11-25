import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";

interface ChatFooterProps {
  /** The teacher is typing. */
  typing: boolean;
  /** Why nothing was sent, or the error. */
  notice: { tone: "status" | "error"; text: string } | null;
}

/** Under the last message: « Le professeur écrit… », the reason for a refusal, the error. */
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
