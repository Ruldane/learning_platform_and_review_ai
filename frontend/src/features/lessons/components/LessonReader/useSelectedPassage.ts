import { useEffect, useState, type RefObject } from "react";
import type { LessonPassage } from "@/shared/lib/lessonPassage";

const MAX_PASSAGE = 1_000;
const normalize = (text: string) => text.replace(/\s+/g, " ").trim();

function selectedPassage(root: HTMLElement, selection: Selection): LessonPassage | null {
  const range = selection.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return null;
  const text = Array.from(normalize(selection.toString())).slice(0, MAX_PASSAGE).join("").trimEnd();
  if (text === "") return null;

  const prefix = document.createRange();
  prefix.selectNodeContents(root);
  prefix.setEnd(range.startContainer, range.startOffset);
  const before = normalize(prefix.toString());
  let occurrence = 0;
  for (let at = before.indexOf(text); at >= 0; at = before.indexOf(text, at + text.length)) {
    occurrence += 1;
  }
  return { text, occurrence };
}

/**
 * The passage the person selected in `target` (trimmed text), `null` when nothing is
 * selected or when the selection leaves the text (table of contents, buttons…).
 */
export function useSelectedPassage(
  target: RefObject<HTMLElement | null>,
  toolbar: RefObject<HTMLElement | null>,
): LessonPassage | null {
  const [passage, setPassage] = useState<LessonPassage | null>(null);

  useEffect(() => {
    const read = () => {
      if (toolbar.current?.contains(document.activeElement)) return;
      const selection = window.getSelection();
      const root = target.current;
      if (!selection || !root || selection.isCollapsed || selection.rangeCount === 0) {
        setPassage(null);
        return;
      }
      setPassage(selectedPassage(root, selection));
    };
    document.addEventListener("selectionchange", read);
    document.addEventListener("focusin", read);
    return () => {
      document.removeEventListener("selectionchange", read);
      document.removeEventListener("focusin", read);
    };
  }, [target, toolbar]);

  return passage;
}
