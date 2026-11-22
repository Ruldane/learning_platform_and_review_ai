import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  enabled: boolean | undefined;
  updating: boolean;
  executing: boolean;
  onToggle: () => void;
  onExecute: () => void;
}

export function RoutineButtons({ enabled, updating, executing, onToggle, onExecute }: Props) {
  const exists = enabled !== undefined;
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="submit" aria-disabled={updating}>
        {t(exists ? "routines.save" : "routines.create")}
      </Button>
      {exists ? (
        <>
          <Button
            type="button"
            variant="outline"
            aria-disabled={updating}
            onClick={() => !updating && onToggle()}
          >
            {t(enabled ? "routines.pause" : "routines.resume")}
          </Button>
          <Button
            type="button"
            variant="outline"
            aria-disabled={executing}
            onClick={() => !executing && onExecute()}
          >
            {t("routines.run")}
          </Button>
        </>
      ) : null}
    </div>
  );
}
