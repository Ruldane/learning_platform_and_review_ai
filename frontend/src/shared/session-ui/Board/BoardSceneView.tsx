import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import type { BinaryFiles } from "@excalidraw/excalidraw/types";
import { lazy, Suspense } from "react";
import { t } from "@/shared/i18n/t";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import type { SceneElementLike } from "../boardTypes";
import { MermaidSvg } from "../MermaidSvg";
import type { BoardApi } from "./boardApi";
import type { BoardScene } from "./useBoardScene";

// Le canevas (Excalidraw et ses styles) n'entre pas dans le paquet principal.
const BoardCanvas = lazy(() => import("./BoardCanvas"));

interface BoardSceneViewProps {
  scene: BoardScene;
  title: string;
  mermaid: string;
  animate: boolean;
  reducedMotion: boolean;
  readOnly: boolean;
  onReady: (api: BoardApi) => void;
  onSceneChange: (elements: readonly SceneElementLike[]) => void;
  /** Texte de l'attente pendant la conversion du schéma. */
  drawingLabel: string;
}

/** Selon la conversion : attente, repli Mermaid simple (SPEC 3.3) ou canevas Excalidraw. */
export function BoardSceneView(props: BoardSceneViewProps) {
  const { scene, title, mermaid, animate, reducedMotion, readOnly } = props;
  if (scene.status === "loading") return <LoadingState label={props.drawingLabel} />;
  if (scene.status === "failed") {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">{t("session.board.fallback")}</p>
        <MermaidSvg code={mermaid} title={title} />
      </div>
    );
  }
  return (
    <Suspense fallback={<LoadingState label={t("session.board.loading")} />}>
      <BoardCanvas
        title={title}
        elements={scene.elements as ExcalidrawElement[]}
        files={scene.files as BinaryFiles}
        animate={animate && scene.animate}
        reducedMotion={reducedMotion}
        readOnly={readOnly}
        onReady={props.onReady}
        onSceneChange={props.onSceneChange}
      />
    </Suspense>
  );
}
