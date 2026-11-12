import { t } from "@/shared/i18n/t";
import { Board, type BoardEdit, type BoardStateView } from "@/shared/session-ui";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface BoardPaneProps {
  states: BoardStateView[];
  /** Les états enregistrés se chargent encore (le direct peut déjà en avoir). */
  loading: boolean;
  failed: boolean;
  onRetry: () => void;
  activeId: string | null;
  onSelect: (id: string) => void;
  onSendEdit: (boardId: string, edit: BoardEdit) => Promise<void>;
  sending: boolean;
  sendError: string | null;
}

/** L'onglet Tableau : états enregistrés puis du direct, retouches de January envoyées aux agents. */
export function BoardPane(props: BoardPaneProps) {
  const { states, loading, failed, onRetry, sendError, ...board } = props;
  if (failed && states.length === 0) {
    return <ErrorState message={t("errors.generic")} onRetry={onRetry} />;
  }
  if (loading && states.length === 0) {
    return <LoadingState label={t("learning.council.boardsLoading")} />;
  }
  return (
    <div className="flex flex-col gap-3">
      {sendError ? <InlineError message={sendError} /> : null}
      <Board states={states} {...board} />
    </div>
  );
}
