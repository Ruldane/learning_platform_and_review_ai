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
  /** Le Scribe dessine cet état pour la première fois : ses éléments apparaissent un par un. */
  animate: boolean;
  readOnly: boolean;
  sending: boolean;
  onSendEdit: (boardId: string, edit: BoardEdit) => void | Promise<void>;
  /** Le canevas de cet état s'est affiché : il ne sera plus animé quand on y reviendra. */
  onSeen: (id: string) => void;
  /** January a des modifications non envoyées sur cet état (ou n'en a plus). */
  onDirtyChange: (id: string, dirty: boolean) => void;
  /** Texte de l'attente pendant la conversion du schéma. */
  drawingLabel: string;
}

/** Un état du tableau : canevas, barre d'actions et repli Mermaid. Remonté à chaque état. */
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
    // Identifiant seulement : jamais le code Mermaid (SPEC 17.4).
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
