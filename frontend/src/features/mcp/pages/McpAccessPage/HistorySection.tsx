import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { CallLog } from "../../components/CallLog";
import { ChangeList } from "../../components/ChangeList";
import { McpSection } from "../../components/McpSection";
import { useHistory } from "../../hooks/useHistory";
import { useUndoChange } from "../../hooks/useUndoChange";

/**
 * L'historique : d'abord les changements qu'on peut défaire (« Annuler » seulement s'ils ne l'ont
 * pas été), puis le journal des appels. Un refus d'annulation (la ligne a changé depuis) s'affiche
 * tel que le serveur le dit.
 */
export function HistorySection() {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const { calls, changes, callViews, changeViews } = useHistory();
  const undo = useUndoChange();
  const failed = calls.error ?? changes.error;
  async function onUndo(callId: string) {
    if (await undo.run(callId)) headingRef.current?.focus();
  }
  function retry() {
    void calls.refetch();
    void changes.refetch();
  }
  return (
    <McpSection
      title={t("mcp.history.title")}
      intro={t("mcp.history.intro")}
      headingRef={headingRef}
    >
      {calls.isPending || changes.isPending ? (
        <LoadingState label={t("mcp.history.loading")} />
      ) : null}
      {failed ? <ErrorState message={errorMessage(failed)} onRetry={retry} /> : null}
      {changes.data ? (
        <>
          <h3 className="font-medium">{t("mcp.history.changes")}</h3>
          <ChangeList changes={changeViews} busyIds={undo.busyIds} onUndo={onUndo} />
          {undo.error ? <InlineError message={undo.error} /> : null}
        </>
      ) : null}
      {calls.data ? (
        <>
          <h3 className="font-medium">{t("mcp.history.calls")}</h3>
          <CallLog calls={callViews} />
        </>
      ) : null}
    </McpSection>
  );
}
