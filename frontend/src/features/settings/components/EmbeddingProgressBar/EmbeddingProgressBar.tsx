import { t } from "@/shared/i18n/t";

/** Shape of `GET /health/embedding` (generated types; not imported: the splitting rule). */
interface EmbeddingProgressView {
  model: string;
  present: boolean;
  /** From 0 to 100; empty while the size is unknown. */
  percent: number | null;
  /** A French text, with no personal data. */
  detail: string;
}

interface EmbeddingProgressBarProps {
  progress?: EmbeddingProgressView;
  /** The last read failed (the next round retries on its own). */
  isError: boolean;
}

function summary({ model, present, percent }: EmbeddingProgressView): string {
  if (present) return t("onboarding.embedding.ready", { model });
  if (percent === null) return t("onboarding.embedding.waiting", { model });
  return t("onboarding.embedding.percent", { model, percent });
}

/**
 * Progress of the embeddings model: the sentence (« bge-m3 : 42 % ») states the status, the bar
 * shows it. An unknown size gives a bar with no value and the server's detail. The zone
 * `status` is always on the page: it only says what is worth announcing (« prêt », or the
 * read impossible), not every percentage reread every 3 s.
 */
export function EmbeddingProgressBar({ progress, isError }: EmbeddingProgressBarProps) {
  const ready = progress?.present === true;
  const announcement = (() => {
    if (isError) return t("onboarding.embedding.unreadable");
    return progress && ready ? summary(progress) : "";
  })();
  return (
    <div className="flex flex-col gap-2">
      <p
        role="status"
        className={`text-sm empty:sr-only ${isError ? "text-destructive" : "font-medium"}`}
      >
        {announcement}
      </p>
      {progress ? (
        <>
          {ready ? null : <p className="text-sm font-medium">{summary(progress)}</p>}
          <progress
            aria-label={t("onboarding.embedding.label")}
            max={100}
            value={progress.percent ?? undefined}
            className="h-2 w-full max-w-md"
          />
          {!progress.present && progress.detail ? (
            <p className="text-sm text-muted-foreground">{progress.detail}</p>
          ) : null}
          {!progress.present ? (
            <p className="text-sm text-muted-foreground">{t("onboarding.embedding.hint")}</p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
