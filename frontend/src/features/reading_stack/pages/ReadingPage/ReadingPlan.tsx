import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useLaunchSource } from "@/shared/session-ui";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { listReadingPrograms, planReading } from "../../api";
import { readingKeys } from "../../queryKeys";
import { ProgramField } from "./ProgramField";

export function ReadingPlan({ id }: { id: string }) {
  const [program, setProgram] = useState("");
  const [open, setOpen] = useState(false);
  const source = useLaunchSource();
  const list = useQuery({
    queryKey: readingKeys.programs,
    enabled: open,
    queryFn: ({ signal }) => listReadingPrograms(signal),
  });
  const start = useMutation({
    mutationFn: (target: string) => planReading(id, target, source.source),
  });
  const error = list.error ?? start.error;
  return (
    <details
      className="rounded-md border p-3"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer text-sm font-medium">{t("reading.actions.plan")}</summary>
      {open ? (
        <div className="mt-3 flex flex-col gap-2">
          <ProgramField programs={list.data} value={program} onChange={setProgram} />
          {source.menu}
          <Button
            className="self-start"
            disabled={!program || start.isPending}
            onClick={() => start.mutate(program)}
          >
            {t("reading.actions.plan")}
          </Button>
          {start.isSuccess ? (
            <Link
              className="self-start text-sm underline"
              to={`/learn/programmes/${start.variables}/replanification`}
            >
              {t("reading.actions.openPlan")}
            </Link>
          ) : null}
          {error ? <InlineError message={errorMessage(error)} /> : null}
        </div>
      ) : null}
    </details>
  );
}
