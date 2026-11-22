import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { Graph } from "../../api";
import { GalaxyCanvas, INITIAL_CAMERA } from "../../components/GalaxyCanvas";
import { GalaxyControls } from "../../components/GalaxyControls";
import { StarList } from "../../components/StarList";
import { GalaxySelection } from "../GalaxySelection";

export function GalaxyWorkspace({ graph }: { graph: Graph }) {
  const [selected, select] = useState<string | null>(null);
  const [camera, setCamera] = useState(INITIAL_CAMERA);
  const node = graph.nodes.find((star) => star.id === selected);
  const rotate = (dx: number, dy: number) => {
    setCamera((view) => ({
      ...view,
      yaw: view.yaw + dx * 0.012,
      pitch: Math.max(-1.5, Math.min(1.5, view.pitch + dy * 0.012)),
    }));
  };
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]">
      <section aria-label={t("galaxy.viewport")} className="flex min-w-0 flex-col gap-3">
        <GalaxyCanvas
          camera={camera}
          edges={graph.edges}
          stars={graph.nodes}
          selected={node?.id ?? null}
          onSelect={select}
          onDrag={rotate}
        />
        <GalaxyControls
          zoom={camera.zoom}
          onRotate={rotate}
          onZoom={(zoom) => setCamera((view) => ({ ...view, zoom }))}
          onReset={() => setCamera(INITIAL_CAMERA)}
        />
        <p className="text-sm text-muted-foreground">{t("galaxy.drag")}</p>
      </section>
      <div className="flex min-w-0 flex-col gap-4">
        <StarList stars={graph.nodes} selected={node?.id ?? null} onSelect={select} />
        <GalaxySelection node={node} graph={graph} onSelect={select} />
      </div>
    </div>
  );
}
