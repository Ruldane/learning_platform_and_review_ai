import { useEffect, useRef } from "react";

/** Délai d'arrêt sur une ligne avant d'offrir de l'aide (option, coupée par défaut). */
export const IDLE_MS = 30_000;

interface IdleOptions {
  /** L'option est cochée dans les préférences. */
  enabled: boolean;
  /** La ligne du curseur ; `null` tant que la personne n'a rien touché. */
  line: number | null;
  /** Change à chaque frappe : taper repart de zéro, sans jamais appeler le professeur. */
  activity: number;
  onIdle: () => void;
}

/**
 * Une minuterie de 30 s : si l'option est cochée et que le curseur reste sur la même ligne sans
 * frappe, `onIdle` part **une seule fois** ; bouger ou taper la réarme. Option coupée : aucune
 * minuterie n'existe.
 */
export function useIdleTeach({ enabled, line, activity, onIdle }: IdleOptions) {
  const latest = useRef(onIdle);
  useEffect(() => {
    latest.current = onIdle;
  });
  useEffect(() => {
    if (!enabled || line === null) return undefined;
    const timer = setTimeout(() => latest.current(), IDLE_MS);
    return () => clearTimeout(timer);
  }, [enabled, line, activity]);
}
