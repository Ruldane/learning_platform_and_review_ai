import { useEffect, useState } from "react";
import type { RefObject } from "react";
import { t } from "@/shared/i18n/t";
import { readingFraction } from "./readingFraction";

interface ReadingProgressProps {
  /** L'article dont on suit la lecture. */
  targetRef: RefObject<HTMLElement | null>;
}

/** Fine barre collée en haut de page : avancement de la lecture de la leçon. */
export function ReadingProgress({ targetRef }: ReadingProgressProps) {
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    function update() {
      const element = targetRef.current;
      if (!element) return;
      const rect = element.getBoundingClientRect();
      setPercent(Math.round(readingFraction(rect, window.innerHeight) * 100));
    }
    update();
    // `capture` : le défilement d'un conteneur interne ne remonte pas jusqu'à la fenêtre.
    window.addEventListener("scroll", update, { capture: true, passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, { capture: true });
      window.removeEventListener("resize", update);
    };
  }, [targetRef]);

  return (
    <div
      role="progressbar"
      aria-label={t("lessons.reader.progress")}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className="sticky top-0 z-10 h-1 w-full bg-muted"
    >
      <div
        className="h-full bg-primary transition-[width] duration-150 motion-reduce:transition-none"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}
