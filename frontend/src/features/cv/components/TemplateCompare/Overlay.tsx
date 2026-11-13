import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { OverlayPage } from "./OverlayPage";

interface OverlayProps {
  originalPages: string[];
  renderPages: string[];
}

/** L'original et le modèle recréé superposés : un curseur (clavier compris) partage la page. */
export function Overlay({ originalPages, renderPages }: OverlayProps) {
  const id = useId();
  const [position, setPosition] = useState(50);
  const count = Math.max(originalPages.length, renderPages.length);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor={id} className="text-sm font-medium">
          {t("cv.template.slider")}
        </label>
        <input
          id={id}
          type="range"
          min={0}
          max={100}
          step={1}
          value={position}
          aria-valuetext={t("cv.template.sliderValue", { percent: position })}
          aria-describedby={`${id}-hint`}
          onChange={(event) => setPosition(Number(event.target.value))}
          className="w-full max-w-md"
        />
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {t("cv.template.sliderHint")}
        </p>
      </div>
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
        {Array.from({ length: count }, (_, index) => (
          <OverlayPage
            key={index}
            n={index + 1}
            original={originalPages[index]}
            render={renderPages[index]}
            position={position}
          />
        ))}
      </div>
    </div>
  );
}
