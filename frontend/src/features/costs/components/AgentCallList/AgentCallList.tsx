import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { useFocusOnMount } from "@/shared/lib/useFocusOnMount";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { formatCount } from "../format";
import type { CallView } from "../viewTypes";
import { CallTable } from "./CallTable";

interface AgentCallListProps {
  calls: CallView[];
  /** Filters are set: the empty state does not simply say « aucun appel ». */
  filtered: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
}

/**
 * The dated journal table, newest first, with « Voir plus » while the
 * server gives a cursor. When the last call arrives after a click, focus moves to the
 * end sentence (the button disappears); the number of calls shown is announced.
 */
export function AgentCallList(props: AgentCallListProps) {
  const { calls, filtered, hasMore, loadingMore, onLoadMore } = props;
  const [requested, setRequested] = useState(false);
  const endRef = useFocusOnMount<HTMLParagraphElement>(requested && !hasMore);
  if (calls.length === 0) {
    const kind = filtered ? "emptyFiltered" : "empty";
    return (
      <EmptyState
        title={t(`costs.log.${kind}.title`)}
        description={t(`costs.log.${kind}.description`)}
      />
    );
  }
  const more = () => {
    if (loadingMore) return;
    setRequested(true);
    onLoadMore();
  };
  const count = t(calls.length === 1 ? "costs.log.countOne" : "costs.log.count", {
    count: formatCount(calls.length),
  });
  return (
    <div className="flex flex-col gap-3">
      <p role="status" className="text-sm text-muted-foreground">
        {count}
      </p>
      <CallTable calls={calls} />
      {hasMore ? (
        <Button variant="outline" aria-disabled={loadingMore} onClick={more} className="self-start">
          {loadingMore ? t("costs.log.loadingMore") : t("costs.log.more")}
        </Button>
      ) : (
        <p ref={endRef} tabIndex={-1} className="text-sm text-muted-foreground outline-none">
          {t("costs.log.end")}
        </p>
      )}
    </div>
  );
}
