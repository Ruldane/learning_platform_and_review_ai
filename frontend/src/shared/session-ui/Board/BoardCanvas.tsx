import "./excalidrawAssets";
import "@excalidraw/excalidraw/index.css";
import { CaptureUpdateAction, Excalidraw } from "@excalidraw/excalidraw";
import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import type { BinaryFiles } from "@excalidraw/excalidraw/types";
import { useEffect, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SceneElementLike } from "../boardTypes";
import type { BoardApi } from "./boardApi";
import { useReveal } from "./useReveal";
import { useSettled } from "./useSettled";

/** Cadre toute la scène, en laissant la place aux barres d'outils d'Excalidraw (haut et bas). */
const FIT = {
  fitToViewport: true,
  viewportZoomFactor: 0.9,
  animate: false,
  canvasOffsets: { top: 72, bottom: 72, left: 16, right: 56 },
} as const;

export interface BoardCanvasProps {
  title: string;
  elements: readonly ExcalidrawElement[];
  files: BinaryFiles;
  /** Les éléments apparaissent un par un (état du Scribe jamais vu) ; sinon la scène est entière. */
  animate: boolean;
  reducedMotion: boolean;
  readOnly: boolean;
  onReady: (api: BoardApi) => void;
  /** Appelé à chaque changement une fois la scène entière affichée (jamais pendant l'animation). */
  onSceneChange: (elements: readonly SceneElementLike[]) => void;
}

/**
 * Le canevas Excalidraw. Chargé par `React.lazy` : Excalidraw (et ses polices) ne pèse que sur
 * l'écran qui affiche un tableau. Pendant l'animation, le canevas est en lecture seule.
 */
export default function BoardCanvas(props: BoardCanvasProps) {
  const { title, elements, files, animate, reducedMotion, readOnly, onReady, onSceneChange } =
    props;
  const { visible, done } = useReveal(elements, { animate, reducedMotion });
  const settled = useSettled(done, !animate || reducedMotion);
  const [initial] = useState(visible);
  const [api, setApi] = useState<BoardApi | null>(null);

  useEffect(() => {
    if (!api) return;
    onReady(api);
    api.scrollToContent(elements as ExcalidrawElement[], FIT);
  }, [api, elements, onReady]);

  useEffect(() => {
    if (!api || visible === initial) return;
    api.updateScene({ elements: visible, captureUpdate: CaptureUpdateAction.NEVER });
  }, [api, visible, initial]);

  useEffect(() => {
    if (api && settled) api.scrollToContent(undefined, FIT);
  }, [api, settled]);

  return (
    <div
      role="region"
      aria-label={t("session.board.canvas", { title })}
      className="h-[34rem] rounded-lg border"
    >
      <Excalidraw
        excalidrawAPI={setApi}
        initialData={{ elements: initial, files, appState: { viewBackgroundColor: "#ffffff" } }}
        viewModeEnabled={readOnly || !settled}
        onChange={(current) => {
          if (settled) onSceneChange(current as readonly SceneElementLike[]);
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
