import { useCallback, useState } from "react";
import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { BoardEdit, BoardStateView } from "../boardTypes";
import { BoardStateList } from "./BoardStateList";
import { BoardWorkspace } from "./BoardWorkspace";

export interface BoardProps {
  states: readonly BoardStateView[];
  /** L'état affiché ; absent ou inconnu : le plus récent. */
  activeId: string | null;
  onSelect: (id: string) => void;
  /** Les modifications de January, envoyées sur demande (bouton), jamais à chaque geste. */
  onSendEdit: (boardId: string, edit: BoardEdit) => void | Promise<void>;
  sending: boolean;
  readOnly?: boolean;
}

function latestOf(states: readonly BoardStateView[]): BoardStateView | undefined {
  return states.reduce<BoardStateView | undefined>(
    (best, state) => (best === undefined || state.step > best.step ? state : best),
    undefined,
  );
}

/**
 * Le tableau que le Scribe remplit pendant le débat (Excalidraw, SPEC 3.3) : liste des états
 * enregistrés, canevas animé, exports et envoi des modifications de January aux agents.
 * Présentationnel : la page lui passe des états de vue et reçoit les modifications (D34).
 */
export function Board(props: BoardProps) {
  const { states, activeId, onSelect, onSendEdit, sending, readOnly = false } = props;
  const [seen, setSeen] = useState<ReadonlySet<string>>(new Set());
  const onSeen = useCallback(
    (id: string) => setSeen((prev) => (prev.has(id) ? prev : new Set(prev).add(id))),
    [],
  );
  const active = states.find((state) => state.id === activeId) ?? latestOf(states);

  if (!active) {
    return <EmptyState title={t("session.board.label")} description={t("session.board.empty")} />;
  }
  return (
    // Mise en page selon la largeur de la zone (et non de l'écran) : dans la colonne de droite du
    // Conseil, la liste des états passe au-dessus du canevas au lieu de lui prendre 14 rem.
    <section aria-label={t("session.board.label")} className="@container">
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
        />
      </div>
    </section>
  );
}
