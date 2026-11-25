import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { addTask } from "../api";
import { programKeys } from "../queryKeys";
import { moduleForDate } from "../toView";
import type { NewTaskInput, ProgramOut } from "../types";

/**
 * Adds a task (`PATCH /programs/{id}`) to the module of the week of the chosen day. A
 * server refusal is set in `error` and rejects the promise, so the form keeps the input.
 */
export function useTaskAdd(programId: string) {
  const client = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const key = programKeys.detail(programId);
  const { mutateAsync } = useMutation({
    mutationFn: ({ input, moduleId }: { input: NewTaskInput; moduleId: string }) =>
      addTask(programId, moduleId, input),
    onError: (failure) => setError(errorMessage(failure)),
    onSettled: () => client.invalidateQueries({ queryKey: key }),
  });

  async function add(input: NewTaskInput): Promise<unknown> {
    setError(null);
    const program = client.getQueryData<ProgramOut>(key);
    const moduleId = program ? moduleForDate(program, input.plannedDate) : null;
    if (moduleId === null) {
      setError(t("program.add.noModule"));
      throw new Error("no module");
    }
    return mutateAsync({ input, moduleId });
  }
  return { add, error };
}
