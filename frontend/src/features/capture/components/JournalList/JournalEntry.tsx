import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { shortDay } from "@/shared/lib/format";
import type { JournalEntryView } from "../viewTypes";

interface JournalEntryProps {
  entry: JournalEntryView;
}

/** A journal line: type spelled out, day, text and links to the session or memory. */
export function JournalEntry({ entry }: JournalEntryProps) {
  const review = entry.kind === "weekly_review";
  return (
    <li
      className={`flex flex-col gap-1 rounded-lg border bg-card px-3 py-2 ${review ? "border-primary" : ""}`}
    >
      <p className="flex flex-wrap items-baseline gap-x-3 text-sm">
        <span className="font-semibold">{t(`capture.journal.kind.${entry.kind}`)}</span>
        <time dateTime={entry.occurredOn} className="text-muted-foreground">
          {shortDay(entry.occurredOn)}
        </time>
      </p>
      <p className="break-words whitespace-pre-line text-sm">{entry.text}</p>
      {entry.studySessionPath || entry.memoryItemId || entry.practicePath ? (
        <p className="flex flex-wrap gap-x-4 text-sm">
          {entry.studySessionPath ? (
            <Link to={entry.studySessionPath} className="underline">
              {t("capture.journal.openStudy")}
            </Link>
          ) : null}
          {entry.practicePath ? (
            <Link to={entry.practicePath} className="underline">
              {t("ghost.journal")}
            </Link>
          ) : null}
          {entry.memoryItemId ? (
            <Link
              to={`/memory?item=${encodeURIComponent(entry.memoryItemId)}`}
              className="underline"
            >
              {t("capture.journal.openMemory")}
            </Link>
          ) : null}
        </p>
      ) : null}
    </li>
  );
}
