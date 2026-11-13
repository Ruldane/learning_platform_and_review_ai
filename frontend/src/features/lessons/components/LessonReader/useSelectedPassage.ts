import { useEffect, useState, type RefObject } from "react";

/**
 * Le passage que la personne a sélectionné dans `target` (texte rogné), `null` quand rien n'est
 * sélectionné ou que la sélection sort du texte (sommaire, boutons…).
 */
export function useSelectedPassage(target: RefObject<HTMLElement | null>): string | null {
  const [passage, setPassage] = useState<string | null>(null);

  useEffect(() => {
    const read = () => {
      const selection = window.getSelection();
      const root = target.current;
      if (!selection || !root || selection.isCollapsed || selection.rangeCount === 0) {
        setPassage(null);
        return;
      }
      const inside = root.contains(selection.getRangeAt(0).commonAncestorContainer);
      const text = inside ? selection.toString().trim() : "";
      setPassage(text === "" ? null : text);
    };
    document.addEventListener("selectionchange", read);
    return () => document.removeEventListener("selectionchange", read);
  }, [target]);

  return passage;
}
