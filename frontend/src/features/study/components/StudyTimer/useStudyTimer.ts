import { useEffect, useRef, useState } from "react";
import type { TimerState } from "../viewTypes";
import { advance, initialTimer } from "./timer";
import { readTimer, writeTimer } from "./timerStorage";

const TICK_MS = 1000;
/**
 * Ce qu'un tour d'horloge peut ajouter, en secondes. Un onglet en arrière-plan est ralenti (un
 * tour par minute au plus) : une minute passe donc encore ; un ordinateur resté en veille, lui, ne
 * compte pas des heures de travail.
 */
const MAX_STEP_SECONDS = 60;

interface Model {
  timer: TimerState;
  /** Nombre de changements de phase : sert à annoncer le dernier. */
  switches: number;
}

/**
 * Le minuteur de la session : travail puis pause, en boucle, en marche dès l'affichage. L'écart
 * est lu sur l'horloge (pas compté en tours) et plafonné ; la pause arrête tout. `onWorkedChange`
 * reçoit le temps de travail, en secondes entières, à chaque seconde gagnée. Avec `storageKey`,
 * l'état est gardé dans `sessionStorage` et repris au montage. `halted` arrête l'horloge sans
 * toucher au choix de la personne (session du Tuteur arrêtée).
 */
export function useStudyTimer(
  workSeconds: number,
  breakSeconds: number,
  onWorkedChange: (seconds: number) => void,
  { storageKey, halted = false }: { storageKey?: string; halted?: boolean } = {},
) {
  const [model, setModel] = useState<Model>(() => ({
    timer: readTimer(storageKey) ?? initialTimer(workSeconds),
    switches: 0,
  }));
  const lastTick = useRef(0);
  const reported = useRef(0);
  const running = model.timer.running && !halted;
  const worked = Math.floor(model.timer.workedSeconds);

  useEffect(() => {
    writeTimer(storageKey, model.timer);
  }, [storageKey, model.timer]);

  useEffect(() => {
    if (!running) return;
    lastTick.current = Date.now();
    const id = setInterval(() => {
      const now = Date.now();
      const elapsed = Math.min(MAX_STEP_SECONDS, (now - lastTick.current) / 1000);
      lastTick.current = now;
      setModel((prev) => {
        const timer = advance(prev.timer, elapsed, workSeconds, breakSeconds);
        return { timer, switches: prev.switches + (timer.phase === prev.timer.phase ? 0 : 1) };
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [running, workSeconds, breakSeconds]);

  useEffect(() => {
    if (worked === reported.current) return;
    reported.current = worked;
    onWorkedChange(worked);
  }, [worked, onWorkedChange]);

  const toggle = () =>
    setModel((prev) => ({ ...prev, timer: { ...prev.timer, running: !prev.timer.running } }));
  return { timer: { ...model.timer, running }, switches: model.switches, toggle };
}
