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
  /** Des filtres sont posés : l'état vide ne dit pas « aucun appel » tout court. */
  filtered: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
}

/**
 * Le journal en tableau daté, du plus récent au plus ancien, avec « Voir plus » tant que le
 * serveur donne un curseur. Quand le dernier appel arrive après un clic, le focus passe à la
 * phrase de fin (le bouton disparaît) ; le nombre d'appels affichés est annoncé.
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
