import { useEffect } from "react";

interface Shortcuts {
  /** Ignore tout : un envoi est en route. */
  busy: boolean;
  flipped: boolean;
  onReveal: () => void;
  onResult: (result: "ok" | "fail") => void;
}

function inTextField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable;
}

function onControl(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest("button, a, summary") !== null;
}

/**
 * Raccourcis d'une fiche : Espace montre la réponse, puis 1 (« Raté ») et 2 (« Su »). Ils vivent sur
 * la fenêtre pour marcher sans avoir mis le focus sur la fiche, mais cèdent la place à un champ de
 * saisie, à une touche combinée (Ctrl, Cmd, Alt) et, pour Espace seulement, à un bouton, un lien ou
 * un résumé qui a le focus : Espace y est déjà son propre clic.
 */
export function useCardShortcuts({ busy, flipped, onReveal, onResult }: Shortcuts) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (busy || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
      if (inTextField(event.target)) return;
      if (event.key === " ") {
        if (flipped || onControl(event.target)) return;
        event.preventDefault();
        onReveal();
      } else if (flipped && event.key === "1") {
        onResult("fail");
      } else if (flipped && event.key === "2") {
        onResult("ok");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, flipped, onReveal, onResult]);
}
