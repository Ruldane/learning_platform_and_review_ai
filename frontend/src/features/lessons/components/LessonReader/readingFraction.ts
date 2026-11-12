/**
 * Part de l'article déjà parcourue, de 0 à 1 : `top` est le haut de l'article par rapport à la
 * fenêtre, `height` sa hauteur, `viewport` la hauteur visible. 1 quand le bas est en vue.
 */
export function readingFraction(rect: { top: number; height: number }, viewport: number): number {
  const scrollable = rect.height - viewport;
  if (scrollable <= 0) return 1;
  return Math.min(1, Math.max(0, -rect.top / scrollable));
}
