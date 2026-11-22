import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import {
  createRoutine,
  executeRoutine,
  updateRoutine,
  type Routine,
  type RoutineAction,
} from "../../api";
import { ROUTINES } from "../../queryKeys";
import { History } from "./History";
import { RoutineButtons } from "./RoutineButtons";

function useRoutineActions(
  action: RoutineAction,
  rule: Routine | undefined,
  onSaved: (hour: string) => void,
) {
  const cache = useQueryClient();
  const change = useMutation({
    mutationFn: (patch: { enabled?: boolean; local_time?: string }) =>
      rule ? updateRoutine(rule.id, patch) : createRoutine(action, patch.local_time ?? "08:30"),
    onSuccess: () => cache.invalidateQueries({ queryKey: ROUTINES }),
  });
  const execute = useMutation({
    mutationFn: ({ id, receipt }: { id: string; receipt: string }) => executeRoutine(id, receipt),
    onSuccess: () => cache.invalidateQueries({ queryKey: ROUTINES }),
  });
  function saveHour(hour: string) {
    if (!change.isPending) {
      change.mutate({ local_time: hour }, { onSuccess: () => onSaved(hour) });
    }
  }
  return { change, execute, saveHour, error: change.error ?? execute.error };
}

export function RoutineEditor({ action, rule }: { action: RoutineAction; rule?: Routine }) {
  const [draft, setDraft] = useState<string | null>(null);
  const hour = draft ?? rule?.local_time ?? "08:30";
  const { change, execute, saveHour, error } = useRoutineActions(action, rule, (saved) => {
    setDraft((current) => (current === saved ? null : current));
  });
  return (
    <>
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          saveHour(hour);
        }}
      >
        <h2 className="text-lg font-semibold">{t(`routines.actions.${action}`)}</h2>
        <label htmlFor="routines-hour">{t("routines.hour")}</label>
        <input
          id="routines-hour"
          className="w-fit rounded-md border bg-background px-3 py-2 focus-visible:outline-2"
          type="time"
          required
          value={hour}
          onChange={(event) => setDraft(event.target.value)}
        />
        <p className="text-sm">{t("routines.timezone")}</p>
        <RoutineButtons
          enabled={rule?.enabled}
          updating={change.isPending}
          executing={execute.isPending}
          onToggle={() => {
            if (rule) change.mutate({ enabled: !rule.enabled });
          }}
          onExecute={() => {
            if (rule) execute.mutate({ id: rule.id, receipt: crypto.randomUUID() });
          }}
        />
        {rule ? (
          <p role="status">{t(rule.enabled ? "routines.active" : "routines.paused")}</p>
        ) : null}
        {error ? <InlineError message={errorMessage(error)} /> : null}
      </form>
      {rule ? <History id={rule.id} action={action} /> : null}
    </>
  );
}
