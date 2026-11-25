/** Half-side of the whole map: the API coordinates fit within [-1, 1], margin included. */
export const HALF = 1.1;
export const MIN_ZOOM = 1;
export const MAX_ZOOM = 8;

/** Window on the map: a zoom (1 to 8) and the centre of what is seen. */
export interface MapView {
  zoom: number;
  cx: number;
  cy: number;
}

export const INITIAL_VIEW: MapView = { zoom: MIN_ZOOM, cx: 0, cy: 0 };

const sizeOf = (zoom: number) => (2 * HALF) / zoom;

/** Keeps the window inside the map. */
function clampCenter(center: number, zoom: number): number {
  const limit = HALF - sizeOf(zoom) / 2;
  return Math.max(-limit, Math.min(limit, center));
}

/** `viewBox` attribute value, rounded to avoid floating-point noise. */
export function viewBoxOf({ zoom, cx, cy }: MapView): string {
  const size = sizeOf(zoom);
  const round = (value: number) => String(Number((value + 0).toFixed(4)));
  return [cx - size / 2, cy - size / 2, size, size].map(round).join(" ");
}

/**
 * Zoom by 2x (`direction` 1 or -1), clamped to 1 to 8. `focus` (0 to 1 in the window) is
 * the point that stays under the cursor; without it, we zoom on the centre.
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

/** Moves the window by `dx`, `dy` screen pixels, for a map shown at `width` pixels. */
export function panned(view: MapView, dx: number, dy: number, width: number): MapView {
  if (width <= 0) return view;
  const unit = sizeOf(view.zoom) / width;
  return {
    ...view,
    cx: clampCenter(view.cx - dx * unit, view.zoom),
    cy: clampCenter(view.cy - dy * unit, view.zoom),
  };
}

/** Recentres the window on a point that leaves it (a keyboard-reached point must stay visible). */
export function revealed(view: MapView, x: number, y: number): MapView {
  const reach = sizeOf(view.zoom) / 2;
  const inside = Math.abs(x - view.cx) <= reach && Math.abs(y - view.cy) <= reach;
  if (inside) return view;
  return { ...view, cx: clampCenter(x, view.zoom), cy: clampCenter(y, view.zoom) };
}
