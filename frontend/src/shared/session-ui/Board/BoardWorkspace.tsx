import { useEffect, useState } from "react";
import type { BoardEdit, BoardStateView, SceneElementLike } from "../boardTypes";
import { BoardSceneView } from "./BoardSceneView";
import { BoardToolbar } from "./BoardToolbar";
import { useBoardActions } from "./useBoardActions";
import { useBoardEdits } from "./useBoardEdits";
import { useBoardScene } from "./useBoardScene";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface BoardWorkspaceProps {
  state: BoardStateView;
  /** The Scribe draws this state for the first time: its elements appear one by one. */
  animate: boolean;
  readOnly: boolean;
  sending: boolean;
  onSendEdit: (boardId: string, edit: BoardEdit) => void | Promise<void>;
  /** This state's canvas has been shown: it will not be animated again when returning to it. */
  onSeen: (id: string) => void;
  /** January has unsent changes on this state (or no longer has any). */
  onDirtyChange: (id: string, dirty: boolean) => void;
  /** Waiting text during the schema conversion. */
  drawingLabel: string;
  saveLabel?: string | undefined;
}

/** A board state: canvas, action bar and Mermaid fallback. Remounted on each state. */
export function BoardWorkspace(props: BoardWorkspaceProps) {
  const { state, readOnly, sending, onSendEdit, onSeen, onDirtyChange } = props;
  const scene = useBoardScene(state);
  const reducedMotion = usePrefersReducedMotion();
  const edits = useBoardEdits(
    scene.status === "ready" ? (scene.elements as SceneElementLike[]) : null,
  );
  const actions = useBoardActions({
    boardId: state.id,
    title: state.title,
    edits,
    onSendEdit,
  });
  const [animate] = useState(props.animate);

  useEffect(() => {
    // Identifier only: never the Mermaid code (SPEC 17.4).
    if (scene.status === "failed") console.error("board_fallback", { boardId: state.id });
    if (scene.status === "ready") onSeen(state.id);
  }, [scene.status, state.id, onSeen]);

  useEffect(() => {
    onDirtyChange(state.id, edits.dirty);
    return () => onDirtyChange(state.id, false);
  }, [edits.dirty, state.id, onDirtyChange]);

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <BoardToolbar
        canExport={actions.api !== null}
        canSend={edits.dirty}
        sending={sending}
        readOnly={readOnly}
        saveLabel={props.saveLabel}
        error={actions.error}
        onExport={(format) => void actions.exportAs(format)}
        onSend={() => void actions.send()}
      />
      <BoardSceneView
        scene={scene}
        title={state.title}
        mermaid={state.mermaid}
        animate={animate}
        reducedMotion={reducedMotion}
        readOnly={readOnly}
        onReady={actions.setApi}
        onSceneChange={edits.onSceneChange}
        drawingLabel={props.drawingLabel}
      />
    </div>
  );
}
