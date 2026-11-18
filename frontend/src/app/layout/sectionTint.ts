import type { CSSProperties } from "react";

/**
 * Teinte d'une section active : fond à 14 % de sa couleur et liseré plein sous l'entrée. La couleur
 * passe par la variable `--section-color` (voir `sectionVars`), posée sur l'élément.
 */
export const ACTIVE_TINT =
  "border-[var(--section-color)] bg-[color-mix(in_srgb,var(--section-color)_14%,transparent)]";

/** Le liseré réservé quand l'entrée n'est pas active : rien ne bouge au changement de page. */
export const IDLE_TINT = "border-transparent";

/** La variable CSS `--section-color` d'une section, à passer à `style`. */
export function sectionVars(color: string): CSSProperties {
  return { "--section-color": color } as CSSProperties;
}
