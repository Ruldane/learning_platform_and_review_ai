/**
 * Share of the article already read, from 0 to 1: `top` is the top of the article relative to the
 * window, `height` its height, `viewport` the visible height. 1 when the bottom is in view.
 */
export function readingFraction(rect: { top: number; height: number }, viewport: number): number {
  const scrollable = rect.height - viewport;
  if (scrollable <= 0) return 1;
  return Math.min(1, Math.max(0, -rect.top / scrollable));
}
