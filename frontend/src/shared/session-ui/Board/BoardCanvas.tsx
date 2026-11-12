import "./excalidrawAssets";
import "@excalidraw/excalidraw/index.css";
import { CaptureUpdateAction, Excalidraw } from "@excalidraw/excalidraw";
import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import type { BinaryFiles } from "@excalidraw/excalidraw/types";
import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SceneElementLike } from "../boardTypes";
import type { BoardApi } from "./boardApi";
import { useFitting } from "./useFitting";
import { useReveal } from "./useReveal";
import { useSettled } from "./useSettled";

export interface BoardCanvasProps {
  title: string;
  elements: readonly ExcalidrawElement[];
  files: BinaryFiles;
  /** Les éléments apparaissent un par un (état du Scribe jamais vu) ; sinon la scène est entière. */
  animate: boolean;
  reducedMotion: boolean;
  readOnly: boolean;
  onReady: (api: BoardApi) => void;
  /**
   * Chaque changement signalé par Excalidraw. `reference` : la scène entière est affichée mais le
   * canevas est encore en lecture seule ; ce sont les ajustements d'Excalidraw, pas January.
   * Rien n'est transmis pendant l'animation.
   */
  onSceneChange: (elements: readonly SceneElementLike[], reference: boolean) => void;
}

/**
 * Le canevas Excalidraw. Chargé par `React.lazy` : Excalidraw (et ses polices) ne pèse que sur
 * l'écran qui affiche un tableau. Pendant l'animation, le canevas est en lecture seule.
 */
export default function BoardCanvas(props: BoardCanvasProps) {
  const { title, elements, files, animate, reducedMotion, readOnly, onReady, onSceneChange } =
    props;
  const { visible, done } = useReveal(elements, { animate, reducedMotion });
  const settled = useSettled(done);
  const [initial] = useState(visible);
  const [api, setApi] = useState<BoardApi | null>(null);
  const frame = useRef<HTMLDivElement>(null);
  useFitting({ api, elements, settled, frame, onReady });

  useEffect(() => {
    if (!api || visible === initial) return;
    api.updateScene({ elements: visible, captureUpdate: CaptureUpdateAction.NEVER });
  }, [api, visible, initial]);

  return (
    <div
      ref={frame}
      role="region"
      aria-label={t("session.board.canvas", { title })}
      className="h-[34rem] rounded-lg border"
    >
      <Excalidraw
        excalidrawAPI={setApi}
        initialData={{ elements: initial, files, appState: { viewBackgroundColor: "#ffffff" } }}
        viewModeEnabled={readOnly || !settled}
        onChange={(current) => {
          if (settled || done) onSceneChange(current as readonly SceneElementLike[], !settled);
        }}
        langCode="fr-FR"
        UIOptions={{
          canvasActions: {
            loadScene: false,
            saveToActiveFile: false,
            export: false,
            saveAsImage: false,
          },
        }}
      />
    </div>
  );
}
