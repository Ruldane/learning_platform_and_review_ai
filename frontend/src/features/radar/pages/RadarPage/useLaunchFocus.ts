import { useEffect } from "react";
import type { StartedRun } from "../../hooks/useStartRadar";

/**
 * Les lancements dont le focus est déjà posé (par objet : un nouveau lancement est un nouvel
 * objet).
 */
const spent = new WeakSet<StartedRun>();

/**
 * Le focus que le lancement de cette page donne au titre du relevé suivi : il ne sert qu'une fois.
 * `starter.started` reste en mémoire tant que la page est montée ; sans cela, un détour par un
 * autre relevé de l'historique puis le retour sur celui-ci (encore en cours) reprendrait le focus
 * alors qu'aucun lancement n'a eu lieu. Le lancement est marqué consommé dans un effet du parent,
 * qui passe après celui du titre (il prend le focus à son montage) : le rendu suivant ne le
 * redemande plus. Aucun état : rien ne se rend de plus.
 */
export function useLaunchFocus(started: StartedRun | null, runId: string | null, running: boolean) {
  const wanted = started !== null && started.runId === runId && !spent.has(started);
  useEffect(() => {
    if (wanted && running) spent.add(started);
  }, [wanted, running, started]);
  return wanted;
}
