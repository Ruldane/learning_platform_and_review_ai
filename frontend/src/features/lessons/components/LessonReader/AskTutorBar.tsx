import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

/** Extrait du passage rappelé dans la barre (le texte complet part au tuteur). */
const EXCERPT_CHARS = 90;

interface AskTutorBarProps {
  passage: string;
  onAsk: (passage: string) => void;
}

/**
 * Barre collée en bas de la fenêtre quand un passage est sélectionné : « Demander au tuteur »
 * ouvre une session sur ce passage. Le bouton ne vole pas la sélection (sinon elle disparaîtrait
 * avant le clic).
 */
export function AskTutorBar({ passage, onAsk }: AskTutorBarProps) {
  const chars = Array.from(passage);
  const excerpt =
    chars.length > EXCERPT_CHARS ? `${chars.slice(0, EXCERPT_CHARS).join("")}…` : passage;
  return (
    <div
      role="region"
      aria-label={t("lessons.reader.askTutorBar")}
      className="sticky bottom-4 z-10 mt-4 flex flex-wrap items-center gap-3 rounded-xl border bg-card p-3 shadow-md"
    >
      <p className="min-w-0 flex-1 text-sm text-muted-foreground">
        {t("lessons.reader.askTutorSelection", { excerpt })}
      </p>
      <Button onMouseDown={(event) => event.preventDefault()} onClick={() => onAsk(passage)}>
        {t("lessons.reader.askTutor")}
      </Button>
    </div>
  );
}
