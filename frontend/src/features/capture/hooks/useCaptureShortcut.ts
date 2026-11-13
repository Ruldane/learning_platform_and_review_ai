import { useEffect } from "react";

/** Ctrl+K sur Windows et Linux, Cmd+K sur Mac, sans autre modificateur. */
function isCaptureShortcut(event: KeyboardEvent): boolean {
  return (
    (event.ctrlKey || event.metaKey) &&
    !event.altKey &&
    !event.shiftKey &&
    !event.isComposing &&
    event.key.toLowerCase() === "k"
  );
}

/**
 * Le raccourci global de la capture : Ctrl+K ou Cmd+K ouvre le dialogue, d'où que l'on soit, y
 * compris dans un champ de saisie (la capture est l'action globale de l'application, et Ctrl+K n'y
 * sert à rien d'autre). Le navigateur ne reçoit pas la touche (pas de barre de recherche).
 */
export function useCaptureShortcut(onOpen: () => void) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!isCaptureShortcut(event)) return;
      event.preventDefault();
      onOpen();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpen]);
}
