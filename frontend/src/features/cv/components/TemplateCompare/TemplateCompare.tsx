import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ZoneView } from "../viewTypes";
import { Overlay } from "./Overlay";
import { ScoreSummary } from "./ScoreSummary";
import { SideBySide } from "./SideBySide";

interface TemplateCompareProps {
  /** Images of the pages of the original CV. */
  originalPages: string[];
  /** Images of the pages of the recreated template. */
  renderPages: string[];
  /** Resemblance score from 0 to 100, or `null` when it is not computed. */
  score: number | null;
  zones: ZoneView[];
  /** The number of adjustments made by the Maquettiste. */
  passes: number;
}

type Mode = "side" | "overlay";

/**
 * The original CV and the recreated template: side by side (default) or overlaid with a slider, the
 * resemblance score and the differing zones, described in sentences.
 */
export function TemplateCompare({
  originalPages,
  renderPages,
  score,
  zones,
  passes,
}: TemplateCompareProps) {
  const [mode, setMode] = useState<Mode>("side");
  if (originalPages.length === 0 && renderPages.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("cv.template.empty")}</p>;
  }
  return (
    <section aria-label={t("cv.template.compare")} className="flex flex-col gap-4">
      <ScoreSummary score={score} zones={zones} passes={passes} />
      <div role="group" aria-label={t("cv.template.mode")} className="flex gap-2">
        <Button
          variant={mode === "side" ? "default" : "outline"}
          aria-pressed={mode === "side"}
          onClick={() => setMode("side")}
        >
          {t("cv.template.side")}
        </Button>
        <Button
          variant={mode === "overlay" ? "default" : "outline"}
          aria-pressed={mode === "overlay"}
          onClick={() => setMode("overlay")}
        >
          {t("cv.template.overlay")}
        </Button>
      </div>
      {mode === "side" ? (
        <SideBySide originalPages={originalPages} renderPages={renderPages} />
      ) : (
        <Overlay originalPages={originalPages} renderPages={renderPages} />
      )}
    </section>
  );
}
