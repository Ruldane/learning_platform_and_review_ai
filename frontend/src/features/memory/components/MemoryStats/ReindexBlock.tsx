import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ReindexView } from "../viewTypes";

interface ReindexBlockProps {
  reindex: ReindexView;
  pending: boolean;
  onReindex: () => void;
}

/** Bouton Réindexer, avancement de la réindexation en cours et son échec éventuel. */
export function ReindexBlock({ reindex, pending, onReindex }: ReindexBlockProps) {
  const active = reindex.status === "queued" || reindex.status === "running";
  return (
    <div className="flex flex-col items-start gap-2">
      {active ? (
        <p role="status" className="text-sm">
          {t("memory.stats.reindexProgress", { done: reindex.done, total: reindex.total })}
        </p>
      ) : null}
      {reindex.status === "failed" && reindex.error ? (
        <InlineError message={reindex.error} />
      ) : null}
      <Button variant="outline" onClick={onReindex} disabled={pending || active}>
        {t("memory.stats.reindex")}
      </Button>
    </div>
  );
}
