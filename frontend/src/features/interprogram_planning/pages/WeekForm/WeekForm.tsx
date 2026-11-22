import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { prepareWeek, sharedWeeksKey, type ProgramOption } from "../../api";
import { nextMonday } from "../../dates";
import { ProgramChoices } from "../ProgramChoices";

export function WeekForm({ options }: { options: ProgramOption[] }) {
  const [week, setWeek] = useState(nextMonday);
  const [selected, setSelected] = useState<string[]>([]);
  const cache = useQueryClient();
  const create = useMutation({
    mutationFn: () => prepareWeek(week, selected),
    onSuccess: () => cache.invalidateQueries({ queryKey: sharedWeeksKey }),
  });
  const canSubmit = week.length > 0 && selected.length >= 2 && !create.isPending;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSubmit) create.mutate();
      }}
    >
      <label className="flex w-fit flex-col gap-1">
        {t("interprogramPlanning.monday")}
        <input
          type="date"
          required
          value={week}
          onChange={(event) => setWeek(event.target.value)}
          className="rounded border border-border bg-background p-2"
        />
      </label>
      <ProgramChoices
        options={options}
        selected={selected}
        onToggle={(id, checked) => {
          setSelected((current) =>
            checked ? [...current, id] : current.filter((item) => item !== id),
          );
        }}
      />
      {create.isError && <p role="alert">{errorMessage(create.error)}</p>}
      <Button type="submit" className="self-start" aria-disabled={!canSubmit}>
        {t("interprogramPlanning.prepare")}
      </Button>
    </form>
  );
}
