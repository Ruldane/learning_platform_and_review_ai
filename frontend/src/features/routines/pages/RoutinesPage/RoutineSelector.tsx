import { t } from "@/shared/i18n/t";
import type { RoutineAction } from "../../api";

const actions = ["due_reviews", "due_transfers", "missions_ending", "due_commitments"] as const;

interface Props {
  selected: RoutineAction;
  onSelect: (action: RoutineAction) => void;
}

export function RoutineSelector({ selected, onSelect }: Props) {
  return (
    <label className="grid w-fit gap-1">
      {t("routines.action")}
      <select
        className="rounded border bg-background p-2"
        value={selected}
        onChange={(event) => {
          const action = actions.find((item) => item === event.target.value);
          if (action) onSelect(action);
        }}
      >
        {actions.map((action) => (
          <option value={action} key={action}>
            {t(`routines.actions.${action}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
