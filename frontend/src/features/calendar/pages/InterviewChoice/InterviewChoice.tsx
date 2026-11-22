import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ChoiceField } from "../../components/ChoiceField";
import { InterviewTiming } from "../../components/InterviewTiming";
import type { ChoiceProps } from "../../forms";
import { useInterviewChoices } from "./useInterviewChoices";

export function InterviewChoice({ initial, pending, onChange, onSelect }: ChoiceProps) {
  const [application, setApplication] = useState(initial);
  const { query: list, dated } = useInterviewChoices();
  const selected = dated.some((row) => row.id === application) ? application : "";
  return (
    <form
      className="flex flex-col items-start gap-3"
      onChange={onChange}
      onSubmit={(event) => {
        event.preventDefault();
        if (pending || !selected) return;
        const fields = new FormData(event.currentTarget);
        onSelect({
          kind: "interview",
          source_id: selected,
          time: String(fields.get("time")),
          minutes: Number(fields.get("minutes")),
        });
      }}
    >
      {list.isPending ? <LoadingState label={t("calendar.loading")} /> : null}
      {list.error ? <p role="alert">{errorMessage(list.error)}</p> : null}
      {list.isSuccess && !dated.length ? <p>{t("calendar.noInterviews")}</p> : null}
      <ChoiceField
        label={t("calendar.interview")}
        value={selected}
        disabled={pending}
        options={dated}
        onChange={setApplication}
        placeholder
      />
      <InterviewTiming disabled={pending} />
      <Button type="submit" disabled={pending || !selected}>
        {t("calendar.preview")}
      </Button>
    </form>
  );
}
