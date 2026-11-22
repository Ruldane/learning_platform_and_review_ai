import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { shortDay } from "@/shared/lib/format";
import { getProgram, getPrograms } from "../../api";

export function useStudyChoices(initial: string) {
  const [program, setProgram] = useState(initial);
  const [task, setTask] = useState("");
  const list = useQuery({
    queryKey: ["calendar", "programs"],
    queryFn: ({ signal }) => getPrograms(signal),
  });
  const valid = list.data?.filter((row) => row.status === "validated") ?? [];
  const selected = valid.some((row) => row.id === program) ? program : "";
  const plan = useQuery({
    queryKey: ["calendar", "programs", selected],
    enabled: Boolean(selected),
    queryFn: ({ signal }) => getProgram(selected, signal),
  });
  const tasks = (plan.data?.weeks ?? [])
    .flatMap((week) => week.modules)
    .filter((module) => !module.skipped)
    .flatMap((module) => module.tasks)
    .filter((row) => row.status === "todo")
    .sort((left, right) => left.planned_date.localeCompare(right.planned_date));
  return {
    pending: list.isPending || (Boolean(selected) && plan.isPending),
    error: list.error ?? plan.error,
    programs: valid.map((row) => ({ id: row.id, label: row.title })),
    tasks: tasks.map((row) => ({
      id: row.id,
      label: shortDay(row.planned_date) + " · " + row.title,
    })),
    task,
    selected,
    setTask,
    setProgram: (id: string) => {
      setProgram(id);
      setTask("");
    },
  };
}
