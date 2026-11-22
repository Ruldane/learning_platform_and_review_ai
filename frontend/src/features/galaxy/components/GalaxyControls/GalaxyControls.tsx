import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface GalaxyControlsProps {
  zoom: number;
  onZoom: (value: number) => void;
  onRotate: (dx: number, dy: number) => void;
  onReset: () => void;
}

const controls = [
  { arrow: "←", key: "galaxy.left", x: -27, y: 0 },
  { arrow: "→", key: "galaxy.right", x: 27, y: 0 },
  { arrow: "↑", key: "galaxy.up", x: 0, y: -27 },
  { arrow: "↓", key: "galaxy.down", x: 0, y: 27 },
] as const;

export function GalaxyControls({ zoom, onZoom, onRotate, onReset }: GalaxyControlsProps) {
  return (
    <div
      role="group"
      aria-label={t("galaxy.controls")}
      className="flex flex-wrap items-center gap-2"
    >
      {controls.map(({ arrow, key, x, y }) => (
        <Button
          key={key}
          size="icon"
          variant="outline"
          aria-label={t(key)}
          onClick={() => onRotate(x, y)}
        >
          {arrow}
        </Button>
      ))}
      <label className="flex items-center gap-2 px-1 text-sm">
        {t("galaxy.zoom")}
        <input
          type="range"
          min={0.65}
          max={2}
          step={0.05}
          value={zoom}
          className="max-w-28 accent-primary outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onChange={(event) => onZoom(event.currentTarget.valueAsNumber)}
        />
      </label>
      <Button variant="ghost" onClick={onReset}>
        {t("galaxy.reset")}
      </Button>
    </div>
  );
}
