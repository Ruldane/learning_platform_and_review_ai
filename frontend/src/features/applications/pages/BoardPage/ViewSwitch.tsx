import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

export type BoardView = "board" | "table";

interface ViewSwitchProps {
  view: BoardView;
  onChange: (view: BoardView) => void;
}

/** Switch Tableau de suivi / Tableau: two buttons; the one shown is announced as « enfoncé ». */
export function ViewSwitch({ view, onChange }: ViewSwitchProps) {
  return (
    <div role="group" aria-label={t("applications.boardPage.viewLabel")} className="flex gap-1">
      {(["board", "table"] as const).map((item) => (
        <Button
          key={item}
          type="button"
          variant={view === item ? "default" : "outline"}
          aria-pressed={view === item}
          onClick={() => onChange(item)}
        >
          {t(
            item === "board"
              ? "applications.boardPage.viewBoard"
              : "applications.boardPage.viewTable",
          )}
        </Button>
      ))}
    </div>
  );
}
