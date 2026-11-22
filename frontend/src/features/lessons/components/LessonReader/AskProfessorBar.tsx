import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import type { LessonPassage } from "@/shared/lib/lessonPassage";
import { Button } from "@/shared/ui/button";

/** Extrait du passage rappelé dans la barre. */
const EXCERPT_CHARS = 90;

interface AskProfessorBarProps {
  passage: LessonPassage;
  onAsk: (passage: LessonPassage) => void;
  barRef: Ref<HTMLDivElement>;
}

/**
 * Barre collée en bas de la fenêtre quand un passage est sélectionné. Le bouton garde
 * la sélection pendant le clic, puis transmet le passage à la leçon.
 */
export function AskProfessorBar({ passage, onAsk, barRef }: AskProfessorBarProps) {
  const chars = Array.from(passage.text);
  const excerpt =
    chars.length > EXCERPT_CHARS ? `${chars.slice(0, EXCERPT_CHARS).join("")}…` : passage.text;
  return (
    <div
      ref={barRef}
      role="region"
      aria-label={t("lessons.reader.askProfessorBar")}
      className="sticky bottom-4 z-10 mt-4 flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3 shadow-md"
    >
      <p className="min-w-0 flex-1 text-sm text-muted-foreground">
        {t("lessons.reader.askProfessorSelection", { excerpt })}
      </p>
      <Button
        type="button"
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => onAsk(passage)}
      >
        {t("lessons.reader.askProfessor")}
      </Button>
    </div>
  );
}
