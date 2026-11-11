/** Demi-côté de la carte entière : les coordonnées de l'API tiennent dans [-1, 1], marge comprise. */
export const HALF = 1.1;
export const MIN_ZOOM = 1;
export const MAX_ZOOM = 8;

/** Fenêtre sur la carte : un zoom (1 à 8) et le centre de ce qu'on voit. */
export interface MapView {
  zoom: number;
  cx: number;
  cy: number;
}

export const INITIAL_VIEW: MapView = { zoom: MIN_ZOOM, cx: 0, cy: 0 };

const sizeOf = (zoom: number) => (2 * HALF) / zoom;

/** Garde la fenêtre à l'intérieur de la carte. */
function clampCenter(center: number, zoom: number): number {
  const limit = HALF - sizeOf(zoom) / 2;
  return Math.max(-limit, Math.min(limit, center));
}

/** Valeur de l'attribut `viewBox`, arrondie pour éviter les bruits de virgule flottante. */
export function viewBoxOf({ zoom, cx, cy }: MapView): string {
  const size = sizeOf(zoom);
  const round = (value: number) => String(Number((value + 0).toFixed(4)));
  return [cx - size / 2, cy - size / 2, size, size].map(round).join(" ");
}

/**
 * Zoom d'un facteur 2 (`direction` 1 ou -1), borné de 1 à 8. `focus` (0 à 1 dans la fenêtre) est
 * le point qui reste sous le curseur ; sans lui, on zoome sur le centre.
 */
export function zoomed(
  view: MapView,
  direction: 1 | -1,
  focus: { x: number; y: number } = { x: 0.5, y: 0.5 },
): MapView {
  const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, view.zoom * 2 ** direction));
  if (zoom === view.zoom) return view;
  const size = sizeOf(view.zoom);
  const anchorX = view.cx - size / 2 + focus.x * size;
  const anchorY = view.cy - size / 2 + focus.y * size;
  const next = sizeOf(zoom);
  return {
    zoom,
    cx: clampCenter(anchorX - (focus.x - 0.5) * next, zoom),
    cy: clampCenter(anchorY - (focus.y - 0.5) * next, zoom),
  };
}

/** Déplace la fenêtre de `dx`, `dy` pixels d'écran, pour une carte affichée sur `width` pixels. */
export function panned(view: MapView, dx: number, dy: number, width: number): MapView {
  if (width <= 0) return view;
  const unit = sizeOf(view.zoom) / width;
  return {
    ...view,
    cx: clampCenter(view.cx - dx * unit, view.zoom),
    cy: clampCenter(view.cy - dy * unit, view.zoom),
  };
}

/** Recentre la fenêtre sur un point s'il en sort (un point atteint au clavier doit se voir). */
export function revealed(view: MapView, x: number, y: number): MapView {
  const reach = sizeOf(view.zoom) / 2;
  const inside = Math.abs(x - view.cx) <= reach && Math.abs(y - view.cy) <= reach;
  if (inside) return view;
  return { ...view, cx: clampCenter(x, view.zoom), cy: clampCenter(y, view.zoom) };
}
