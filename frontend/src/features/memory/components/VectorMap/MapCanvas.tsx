import { useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { MapPointView } from "../viewTypes";
import { MapPointDot } from "./MapPointDot";
import { viewBoxOf } from "./mapView";
import { useMapView } from "./useMapView";

interface MapCanvasProps {
  points: MapPointView[];
  onOpen: (itemId: string) => void;
}

/** Commandes de zoom et surface SVG de la carte (la fenêtre vit ici, tant qu'il y a des points). */
export function MapCanvas({ points, onOpen }: MapCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const map = useMapView(svgRef);
  return (
    <>
      <div role="toolbar" aria-label={t("memory.map.controls")} className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={map.zoomIn} disabled={!map.canZoomIn}>
          {t("memory.map.zoomIn")}
        </Button>
        <Button variant="outline" onClick={map.zoomOut} disabled={!map.canZoomOut}>
          {t("memory.map.zoomOut")}
        </Button>
        <Button variant="outline" onClick={map.reset} disabled={!map.canZoomOut}>
          {t("memory.map.reset")}
        </Button>
      </div>
      <svg
        ref={svgRef}
        role="group"
        aria-label={t("memory.map.label")}
        viewBox={viewBoxOf(map.view)}
        style={{ touchAction: map.canZoomOut ? "none" : "pan-y" }}
        className="aspect-square max-h-[70vh] w-full rounded-xl border border-border bg-card"
        {...map.handlers}
      >
        {points.map((point) => (
          <MapPointDot
            key={point.item_id}
            point={point}
            zoom={map.view.zoom}
            onClick={() => {
              if (!map.wasDragged()) onOpen(point.item_id);
            }}
            onActivate={() => onOpen(point.item_id)}
            onFocus={() => map.reveal(point.x, point.y)}
          />
        ))}
      </svg>
    </>
  );
}
