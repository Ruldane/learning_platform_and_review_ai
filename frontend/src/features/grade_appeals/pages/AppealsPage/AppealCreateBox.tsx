import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { APPEALS, createAppeal, listCriteria, listProjects } from "../../api";

function useAppealForm() {
  const [project, setProject] = useState("");
  const [criterion, setCriterion] = useState("");
  const [reason, setReason] = useState("");
  const sources = useQuery({ queryKey: ["appeal-projects"], queryFn: ({ signal }) => listProjects(signal) });
  const criteria = useQuery({
    queryKey: ["appeal-criteria", project],
    queryFn: ({ signal }) => listCriteria(project, signal),
    enabled: Boolean(project),
  });
  const navigate = useNavigate();
  const queries = useQueryClient();
  const create = useMutation({
    mutationFn: createAppeal,
    onSuccess: async (row) => {
      await queries.invalidateQueries({ queryKey: APPEALS });
      void navigate(`/skills/appeals/${row.id}`);
    },
  });
  const changeProject = (id: string) => {
    setProject(id);
    setCriterion("");
  };
  return { project, changeProject, criterion, setCriterion, reason, setReason, sources, criteria, create };
}

export function AppealCreateBox() {
  const id = useId();
  const form = useAppealForm();
  const chosen = form.criteria.data?.find((item) => String(item.index) === form.criterion);
  const valid = Boolean(form.project && chosen && form.reason.trim());
  return (
    <form className="grid gap-3 rounded-xl border bg-card p-4" onSubmit={(event) => {
      event.preventDefault();
      if (valid && chosen) form.create.mutate({
        project_id: form.project, criterion_index: chosen.index, reason: form.reason,
      });
    }}>
      <label htmlFor={`${id}-project`}>{t("gradeAppeals.source")}</label>
      <select id={`${id}-project`} className={fieldClass} value={form.project} onChange={(event) => form.changeProject(event.target.value)}>
        <option value="">{t("gradeAppeals.chooseProject")}</option>
        {form.sources.data?.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
      </select>
      {form.sources.error ? <ErrorState message={errorMessage(form.sources.error)} onRetry={() => void form.sources.refetch()} /> : null}
      <label htmlFor={`${id}-criterion`}>{t("gradeAppeals.criterion")}</label>
      <select id={`${id}-criterion`} className={fieldClass} value={form.criterion} onChange={(event) => form.setCriterion(event.target.value)}>
        <option value="">{t("gradeAppeals.chooseCriterion")}</option>
        {form.criteria.data?.map((item) => (
          <option key={item.index} value={item.index}>{item.criterion}</option>
        ))}
      </select>
      {form.criteria.data?.length === 0 ? <p>{t("gradeAppeals.noCriteria")}</p> : null}
      {form.criteria.error ? <ErrorState message={errorMessage(form.criteria.error)} onRetry={() => void form.criteria.refetch()} /> : null}
      {chosen?.original_comment ? <p className="text-sm">{chosen.original_comment}</p> : null}
      <label htmlFor={`${id}-reason`}>{t("gradeAppeals.reason")}</label>
      <textarea id={`${id}-reason`} className={fieldClass} value={form.reason} rows={4} maxLength={3500} onChange={(event) => form.setReason(event.target.value)} />
      <Button type="submit" className="justify-self-start" disabled={!valid || form.create.isPending}>
        {t("gradeAppeals.create")}
      </Button>
      {form.create.error ? <InlineError message={errorMessage(form.create.error)} /> : null}
    </form>
  );
}
