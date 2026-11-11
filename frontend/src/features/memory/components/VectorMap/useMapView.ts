import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type PointerEvent,
  type RefObject,
  type SetStateAction,
} from "react";
import {
  INITIAL_VIEW,
  MAX_ZOOM,
  MIN_ZOOM,
  panned,
  revealed,
  zoomed,
  type MapView,
} from "./mapView";

/** En dessous de ce déplacement (pixels), un appui sur un point reste un clic, pas un glissement. */
const DRAG_THRESHOLD = 4;

/** Position du curseur dans la carte, de 0 à 1 (le centre si la carte n'a pas de taille). */
function focusOf(svg: SVGSVGElement, clientX: number, clientY: number) {
  const rect = svg.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return { x: 0.5, y: 0.5 };
  return { x: (clientX - rect.left) / rect.width, y: (clientY - rect.top) / rect.height };
}

/** Molette : zoom vers le curseur. */
function useWheelZoom(
  svgRef: RefObject<SVGSVGElement | null>,
  setView: Dispatch<SetStateAction<MapView>>,
) {
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    // Écouteur natif : React attache `wheel` en mode passif, et la page défilerait en même temps.
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const focus = focusOf(svg, event.clientX, event.clientY);
      setView((current) => zoomed(current, event.deltaY < 0 ? 1 : -1, focus));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [svgRef, setView]);
}

/** Zoom (boutons, molette) et déplacement (glisser) de la carte, bornés à la carte entière. */
export function useMapView(svgRef: RefObject<SVGSVGElement | null>) {
  const [view, setView] = useState<MapView>(INITIAL_VIEW);
  const drag = useRef<{ x: number; y: number; travelled: number } | null>(null);
  const justDragged = useRef(false);
  useWheelZoom(svgRef, setView);

  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    justDragged.current = false;
    if (view.zoom > MIN_ZOOM) drag.current = { x: event.clientX, y: event.clientY, travelled: 0 };
  };
  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const start = drag.current;
    const width = svgRef.current?.getBoundingClientRect().width ?? 0;
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    start.travelled += Math.abs(dx) + Math.abs(dy);
    start.x = event.clientX;
    start.y = event.clientY;
    if (start.travelled > DRAG_THRESHOLD) justDragged.current = true;
    setView((current) => panned(current, dx, dy, width));
  };
  const endDrag = () => {
    drag.current = null;
  };

  return {
    view,
    canZoomIn: view.zoom < MAX_ZOOM,
    canZoomOut: view.zoom > MIN_ZOOM,
    zoomIn: () => setView((current) => zoomed(current, 1)),
    zoomOut: () => setView((current) => zoomed(current, -1)),
    reset: () => setView(INITIAL_VIEW),
    reveal: useCallback((x: number, y: number) => setView((cur) => revealed(cur, x, y)), []),
    /** Vrai si l'appui en cours est un glissement : le clic qui suit ne doit pas ouvrir un point. */
    wasDragged: () => justDragged.current,
    handlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onPointerLeave: endDrag,
    },
  };
}
