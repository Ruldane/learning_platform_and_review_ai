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
  /** Elements appear one by one (a state the Scribe has not shown yet); otherwise all at once. */
  animate: boolean;
  reducedMotion: boolean;
  readOnly: boolean;
  onReady: (api: BoardApi) => void;
  /**
   * Each change reported by Excalidraw. `reference`: the whole scene is shown but the
   * canvas is still read-only; these are Excalidraw's adjustments, not January's.
   * Nothing is sent during the animation.
   */
  onSceneChange: (elements: readonly SceneElementLike[], reference: boolean) => void;
}

/** Scene identity: each Excalidraw adjustment bumps the version of an element. */
function sceneKey(elements: readonly { id: string; version?: number }[]): string {
  return elements.map((el) => `${el.id}@${el.version}`).join("|");
}

/**
 * The Excalidraw canvas. Loaded by `React.lazy`: Excalidraw (and its fonts) only weighs on
 * the screen showing a board. During the animation, the canvas is read-only.
 */
export default function BoardCanvas(props: BoardCanvasProps) {
  const { title, elements, files, animate, reducedMotion, readOnly, onReady, onSceneChange } =
    props;
  const { visible, done } = useReveal(elements, { animate, reducedMotion });
  const [changeTick, setChangeTick] = useState(0);
  const settled = useSettled(done, changeTick);
  const lastKey = useRef<string | null>(null);
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
          if (!settled && !done) return;
          onSceneChange(current as readonly SceneElementLike[], !settled);
          if (settled) return;
          // An Excalidraw adjustment before things settle restarts the wait. Excalidraw calls
          // `onChange` on each update, even with nothing changed: only a modified scene
          // counts, otherwise this render would trigger another one, endlessly.
          const key = sceneKey(current);
          if (key === lastKey.current) return;
          lastKey.current = key;
          setChangeTick((tick) => tick + 1);
        }}
        langCode="en"
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
