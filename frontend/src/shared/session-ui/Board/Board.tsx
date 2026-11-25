import { useCallback, useState } from "react";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { BoardEdit, BoardLabels, BoardStateView } from "../boardTypes";
import { BoardStateList } from "./BoardStateList";
import { BoardWorkspace } from "./BoardWorkspace";

export interface BoardProps {
  states: readonly BoardStateView[];
  /**
   * The state displayed; absent or unknown: the most recent, unless January edits a state without
   * having sent their changes (it stays displayed when the Scribe publishes a new one).
   */
  activeId: string | null;
  onSelect: (id: string) => void;
  /** January's changes, sent on request (button), never on each gesture. */
  onSendEdit: (boardId: string, edit: BoardEdit) => void | Promise<void>;
  onDirtyChange?: (dirty: boolean) => void;
  sending: boolean;
  readOnly?: boolean;
  /** Page-specific texts (title, empty table, drawing in progress); when absent, the Scribe's. */
  labels?: BoardLabels;
}

function latestOf(states: readonly BoardStateView[]): BoardStateView | undefined {
  return states.reduce<BoardStateView | undefined>(
    (best, state) => (best === undefined || state.step > best.step ? state : best),
    undefined,
  );
}

/**
 * The board the Scribe fills during the debate (Excalidraw, SPEC 3.3): list of saved
 * states, animated canvas, exports and sending January's changes to the agents.
 * Presentational: the page passes it view states and receives the changes (D34).
 */
export function Board(props: BoardProps) {
  const { states, activeId, onSelect, onSendEdit, sending, readOnly = false, onDirtyChange } = props;
  const labels = props.labels ?? {
    label: t("session.board.label"),
    empty: t("session.board.empty"),
    drawing: t("session.board.converting"),
  };
  const [seen, setSeen] = useState<ReadonlySet<string>>(new Set());
  const onSeen = useCallback(
    (id: string) => setSeen((prev) => (prev.has(id) ? prev : new Set(prev).add(id))),
    [],
  );
  // Edited state not yet sent: a new Scribe state does not replace it on screen.
  const [editing, setEditing] = useState<string | null>(null);
  const trackEdit = useCallback(
    (id: string, dirty: boolean) => {
      setEditing((prev) => (dirty ? id : prev === id ? null : prev));
      onDirtyChange?.(dirty);
    },
    [onDirtyChange],
  );
  const find = (id: string | null) => states.find((state) => state.id === id);
  const active = find(activeId) ?? find(editing) ?? latestOf(states);

  if (!active) {
    return <EmptyState title={labels.label} description={labels.empty} />;
  }
  return (
    // Layout by the width of the area (not the screen): in the Council's right column, the state
    // list goes above the canvas instead of taking 14 rem from it.
    <section aria-label={labels.label} className="@container">
      <div className="grid gap-4 @2xl:grid-cols-[14rem_minmax(0,1fr)]">
        <BoardStateList states={states} activeId={active.id} onSelect={onSelect} />
        <BoardWorkspace
          key={active.id}
          state={active}
          animate={!seen.has(active.id)}
          readOnly={readOnly}
          sending={sending}
          onSendEdit={onSendEdit}
          onSeen={onSeen}
          onDirtyChange={trackEdit}
          drawingLabel={labels.drawing}
          saveLabel={labels.save}
        />
      </div>
    </section>
  );
}
