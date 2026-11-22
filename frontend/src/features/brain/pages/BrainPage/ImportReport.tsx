import { t } from "@/shared/i18n/t";
import type { FolderStatus } from "../../api";

const REASONS = [
  "technical",
  "link",
  "extension",
  "binary",
  "tooLarge",
  "path",
  "special",
  "unreadable",
  "changed",
] as const;

export function ImportReport({ status }: { status?: FolderStatus }) {
  if (!status) return <p className="text-sm text-muted-foreground">{t("brain.waiting")}</p>;
  const { indexed, total, queued, processing, error, report } = status;
  return (
    <div className="grid gap-1 text-sm">
      <p>{t("brain.indexed", { indexed, total })}</p>
      {queued || processing ? <p>{t("brain.pending", { count: queued + processing })}</p> : null}
      {error ? <p>{t("brain.errors", { count: error })}</p> : null}
      {report ? (
        <details className="rounded-md bg-muted p-2">
          <summary className="cursor-pointer font-medium">
            {t(`brain.report.${report.state}`)}
          </summary>
          <p className="mt-1">
            {t("brain.counts", {
              scanned: report.scanned,
              added: report.added,
              changed: report.changed,
              removed: report.removed,
              errors: report.errors,
            })}
          </p>
          <ul className="text-muted-foreground">
            {REASONS.map((reason) =>
              report.ignored[reason] ? (
                <li key={reason}>
                  {t(`brain.ignored.${reason}`)} {report.ignored[reason]}
                </li>
              ) : null,
            )}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
