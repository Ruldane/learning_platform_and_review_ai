import { useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ZoneView } from "../viewTypes";
import { Overlay } from "./Overlay";
import { ScoreSummary } from "./ScoreSummary";
import { SideBySide } from "./SideBySide";

interface TemplateCompareProps {
  /** Les images des pages du CV d'origine. */
  originalPages: string[];
  /** Les images des pages du modèle recréé. */
  renderPages: string[];
  /** Score de ressemblance de 0 à 100, ou `null` s'il n'est pas calculé. */
  score: number | null;
  zones: ZoneView[];
  /** Le nombre d'ajustements faits par le Maquettiste. */
  passes: number;
}

type Mode = "side" | "overlay";

/**
 * Le CV d'origine et le modèle recréé : côte à côte (par défaut) ou superposés avec un curseur, le
 * score de ressemblance et les zones qui diffèrent, dites en phrases.
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
